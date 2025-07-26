import time
from datetime import datetime

from loguru import logger
from sqlalchemy import or_, and_
from tqdm import tqdm

from apis.xhs_pc_apis import XHS_Apis
from db.database import SessionLocal
from db.models import Rednote
from server import config
from xhs_utils.data_util import handle_note_info, download_note

# 配置日志输出
logger.add("logs/spider_{time}.log", rotation="500 MB", encoding="utf-8", enqueue=True, retention="10 days")


def save_note_to_db(note_info):
    """
    将单个笔记信息保存到数据库
    :param note_info:
    :return:
    """
    session = SessionLocal()
    try:
        # 检查是否已存在
        existing_note = session.query(Rednote).filter(Rednote.note_id == note_info['note_id']).first()

        if existing_note:
            # 更新现有记录
            existing_note.note_url = note_info.get('note_url')
            existing_note.note_type = note_info.get('note_type')
            existing_note.user_id = note_info.get('user_id')
            existing_note.home_url = note_info.get('home_url')
            existing_note.nickname = note_info.get('nickname')
            existing_note.avatar = note_info.get('avatar')
            existing_note.title = note_info.get('title')
            existing_note.desc = note_info.get('desc')
            existing_note.liked_count = note_info.get('liked_count', 0)
            existing_note.collected_count = note_info.get('collected_count', 0)
            existing_note.comment_count = note_info.get('comment_count', 0)
            existing_note.share_count = note_info.get('share_count', 0)
            existing_note.video_cover = note_info.get('video_cover')
            existing_note.video_addr = note_info.get('video_addr')
            existing_note.image_list = note_info.get('image_list', [])
            existing_note.tags = note_info.get('tags', [])
            existing_note.upload_time = datetime.strptime(note_info.get('upload_time'),
                                                          "%Y-%m-%d %H:%M:%S") if note_info.get(
                'upload_time') else None
            existing_note.ip_location = note_info.get('ip_location')
            existing_note.last_update_time = datetime.now()
        else:
            # 创建新记录
            db_note = Rednote(
                note_id=note_info.get('note_id'),
                note_url=note_info.get('note_url'),
                note_type=note_info.get('note_type'),
                user_id=note_info.get('user_id'),
                home_url=note_info.get('home_url'),
                nickname=note_info.get('nickname'),
                avatar=note_info.get('avatar'),
                title=note_info.get('title'),
                description=note_info.get('desc'),
                liked_count=note_info.get('liked_count', 0),
                collected_count=note_info.get('collected_count', 0),
                comment_count=note_info.get('comment_count', 0),
                share_count=note_info.get('share_count', 0),
                video_cover=note_info.get('video_cover'),
                video_addr=note_info.get('video_addr'),
                image_list=note_info.get('image_list', []),
                tags=note_info.get('tags', []),
                upload_time=datetime.strptime(note_info.get('upload_time'), "%Y-%m-%d %H:%M:%S") if note_info.get(
                    'upload_time') else None,
                ip_location=note_info.get('ip_location'),
                last_update_time=datetime.now()
            )
            session.add(db_note)

        session.commit()
        logger.info(f"笔记 {note_info.get('note_id')} 已保存到数据库")
        return True
    except Exception as e:
        session.rollback()
        logger.error(f"保存笔记 {note_info.get('note_id')} 到数据库时出错: {e}")
        return False
    finally:
        session.close()


def download_note_media():
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import threading

    local = threading.local()

    def get_session():
        if not hasattr(local, 'session'):
            local.session = SessionLocal()
        return local.session

    def download_single_note(note_info):
        session = get_session()
        save_path = download_note(note_info, config.REDNOTE_DIR)
        if save_path:
            logger.info(f"笔记 {note_info.note_id} 下载成功，保存路径: {save_path}")
            try:
                db_note = session.query(Rednote).filter(Rednote.note_id == note_info.note_id).first()
                if db_note:
                    if note_info.note_type == '图集':
                        db_note.image_download_at = datetime.now()
                    elif note_info.note_type == '视频':
                        db_note.video_download_at = datetime.now()
                    session.commit()
                return True, note_info.note_id, save_path
            except Exception as e:
                session.rollback()
                logger.error(f"更新笔记 {note_info.note_id} 下载时间时出错: {e}")
                return False, note_info.note_id, str(e)
        else:
            logger.error(f"笔记 {note_info.note_id} 下载失败")
            return False, note_info.note_id, "下载失败"

    session = SessionLocal()
    rednoteList = (session.query(Rednote)
                   .filter(or_(
        # 图文笔记：image_download_at 为空
        and_(Rednote.note_type == '图集', Rednote.image_download_at == None),
        # 视频笔记：video_download_at 为空
        and_(Rednote.note_type == '视频', Rednote.video_download_at == None)
    ))
                   .all())
    if not rednoteList:
        print("没有需要下载的帖子")
        session.close()
        return

    start_time = time.time()
    success_count = 0

    # 使用线程池进行多线程下载
    with ThreadPoolExecutor(max_workers=5) as executor:
        # 提交所有任务
        future_to_note = {executor.submit(download_single_note, note_info): note_info for note_info in rednoteList}

        # 处理完成的任务
        for future in tqdm(as_completed(future_to_note), total=len(rednoteList), desc="下载小红书", unit="note"):
            try:
                success, note_id, result = future.result()
                if success:
                    success_count += 1
                else:
                    logger.error(f"笔记 {note_id} 处理失败: {result}")
            except Exception as e:
                note_info = future_to_note[future]
                logger.error(f"处理笔记 {note_info.note_id} 时发生异常: {e}")

    elapsed = time.time() - start_time
    session.close()
    print(f"✅ 小红书帖子下载完成，共处理 {success_count} 条，用时 {elapsed:.2f} 秒")


class DataSpider:
    def __init__(self):
        self.xhs_apis = XHS_Apis()

    def spider_note(self, note_url: str, cookies_str: str, proxies=None):
        """
        爬取一个笔记的信息
        :param note_url:
        :param cookies_str:
        :return:
        """
        note_info = None
        try:
            success, msg, note_info = self.xhs_apis.get_note_info(note_url, cookies_str, proxies)
            if success:
                note_info = note_info['data']['items'][0]
                note_info['url'] = note_url
                note_info = handle_note_info(note_info)
        except Exception as e:
            success = False
            msg = e
        logger.info(f'爬取笔记信息 {note_url}: {success}, msg: {msg}')
        return success, msg, note_info

    def spider_some_note(self, notes: list, cookies_str: str, proxies=None):
        """
        爬取一些笔记的信息
        :param notes:
        :param cookies_str:
        :param base_path:
        :return:
        """
        note_list = []

        for note_url in notes:
            success, msg, note_info = self.spider_note(note_url, cookies_str, proxies)
            if not success:
                logger.error(f'爬取失败，停止继续爬取。失败原因: {msg}')
                # 如果已经爬取到了一些数据，保存现有数据
                if note_list:
                    logger.info(f'保存已爬取的 {len(note_list)} 个笔记')
                    for note_info in note_list:
                        save_note_to_db(note_info)
                return False, msg, note_list

            if note_info is not None:
                note_list.append(note_info)
                save_note_to_db(note_info)
                logger.info(f'成功爬取笔记: {note_info["note_id"]}')

        logger.info(f'成功爬取 {len(note_list)} 个笔记')

        return True, "success", note_list

    def spider_user_collect_note(self, user_url: str, cookies_str: str, proxies=None):
        """
        爬取一个用户的收藏笔记
        :param user_url:
        :param cookies_str:
        :param base_path:
        :return:
        """
        note_list = []
        try:
            success, msg, all_note_info = self.xhs_apis.get_user_all_collect_note_info(user_url, cookies_str, proxies)
            print(all_note_info)
            if success:
                logger.info(f'用户 {user_url} 作品数量: {len(all_note_info)}')
                for simple_note_info in all_note_info:
                    note_url = f"https://www.xiaohongshu.com/explore/{simple_note_info['note_id']}?xsec_token={simple_note_info['xsec_token']}"
                    note_list.append(note_url)
            self.spider_some_note(note_list, cookies_str)
        except Exception as e:
            success = False
            msg = e
        logger.info(f'爬取用户所有收藏视频 {user_url}: {success}, msg: {msg}')
        return note_list, success, msg

    def spider_user_favorite_note(self, user_url: str, cookies_str: str, proxies=None):
        """
        爬取一个用户的点赞笔记
        :param user_url:
        :param cookies_str:
        :param base_path:
        :return:
        """
        note_list = []
        try:
            success, msg, all_note_info = self.xhs_apis.get_user_all_like_note_info(user_url, cookies_str, proxies)
            if success:
                logger.info(f'用户 {user_url} 作品数量: {len(all_note_info)}')
                for simple_note_info in all_note_info:
                    note_url = f"https://www.xiaohongshu.com/explore/{simple_note_info['note_id']}?xsec_token={simple_note_info['xsec_token']}"
                    note_list.append(note_url)
            self.spider_some_note(note_list, cookies_str, proxies)
        except Exception as e:
            success = False
            msg = e
        logger.info(f'爬取用户所有视频 {user_url}: {success}, msg: {msg}')
        return note_list, success, msg


if __name__ == '__main__':

    # data_spider = DataSpider()
    #
    # with open('/Users/yueyong/Dev/llm/Alfred/cookie_file.txt', 'r', encoding='utf-8') as f:
    #     REDNOTE_COOKIES = f.read()
    # user_url = 'https://www.xiaohongshu.com/user/profile/5c1313b60000000007003641'
    # data_spider.spider_user_collect_note(user_url, REDNOTE_COOKIES)
    download_note_media()