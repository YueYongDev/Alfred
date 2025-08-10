import smtplib
import os
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from sqlalchemy.orm import Session
from jinja2 import Template
from loguru import logger

from db.database import SessionLocal
from db.models import DailyHot


def get_top_hot_items(limit: int = 5) -> list:
    """
    获取已经总结过的、hot score分数最多的、最新的5条热点内容

    :param limit: 返回的热点数量，默认为5
    :return: 热点数据列表
    """
    session: Session = SessionLocal()
    try:
        # 查询已经总结过的热点数据（有ai_summary和ai_tags），按hot_score和publish_time排序
        hot_items = session.query(DailyHot).filter(
            DailyHot.ai_summary.isnot(None),
            DailyHot.ai_tags.isnot(None),
            DailyHot.hot_score.isnot(None),
            DailyHot.publish_time.isnot(None)
        ).order_by(
            DailyHot.hot_score.desc(),  # 按hot_score降序排列
            DailyHot.publish_time.desc()  # 按发布时间降序排列
        ).limit(limit).all()

        # 转换为字典列表以便处理
        result = []
        for item in hot_items:
            result.append({
                'id': item.id,
                'category': item.category,
                'title': item.title,
                'description': item.description,
                'cover': item.cover,
                'hot_score': item.hot_score,
                'url': item.url,
                'mobile_url': item.mobile_url,
                'publish_time': item.publish_time.strftime('%Y-%m-%d %H:%M:%S') if item.publish_time else None,
                'ai_summary': item.ai_summary,
                'ai_tags': item.ai_tags,
                'collected_at': item.collected_at.strftime('%Y-%m-%d %H:%M:%S') if item.collected_at else None
            })

        logger.info(f"获取到 {len(result)} 条热点数据")
        return result
    except Exception as e:
        logger.error(f"获取热点数据时出错: {e}")
        return []
    finally:
        session.close()


def generate_html_content(hot_items: list) -> str:
    """
    生成HTML格式的邮件内容

    :param hot_items: 热点数据列表
    :return: HTML内容
    """
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>每日热点摘要</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .container {
                max-width: 800px;
                margin: 0 auto;
                background-color: white;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                padding: 30px;
            }
            .header {
                text-align: center;
                border-bottom: 2px solid #eee;
                padding-bottom: 20px;
                margin-bottom: 30px;
            }
            .header h1 {
                color: #333;
                margin: 0;
            }
            .header p {
                color: #666;
                margin: 5px 0 0 0;
            }
            .hot-item {
                border-bottom: 1px solid #eee;
                padding: 20px 0;
            }
            .hot-item:last-child {
                border-bottom: none;
            }
            .item-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 10px;
            }
            .item-title {
                font-size: 18px;
                font-weight: bold;
                color: #333;
                margin: 0;
            }
            .hot-score {
                background-color: #ff6b35;
                color: white;
                padding: 3px 8px;
                border-radius: 12px;
                font-size: 14px;
                font-weight: bold;
            }
            .item-category {
                color: #ff6b35;
                font-weight: bold;
                font-size: 14px;
                margin: 5px 0;
            }
            .item-description {
                color: #666;
                line-height: 1.5;
                margin: 10px 0;
            }
            .item-summary {
                background-color: #f8f9fa;
                border-left: 4px solid #ff6b35;
                padding: 15px;
                margin: 15px 0;
                border-radius: 0 4px 4px 0;
            }
            .item-summary p {
                margin: 0;
                color: #444;
                line-height: 1.6;
            }
            .item-tags {
                margin: 15px 0;
            }
            .tag {
                display: inline-block;
                background-color: #e9ecef;
                color: #495057;
                padding: 4px 10px;
                border-radius: 15px;
                font-size: 12px;
                margin-right: 8px;
                margin-bottom: 8px;
            }
            .item-link {
                margin-top: 10px;
            }
            .item-link a {
                color: #007bff;
                text-decoration: none;
                font-weight: bold;
            }
            .item-link a:hover {
                text-decoration: underline;
            }
            .item-time {
                color: #999;
                font-size: 12px;
                margin-top: 5px;
            }
            .footer {
                text-align: center;
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #eee;
                color: #999;
                font-size: 12px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔥 每日热点摘要</h1>
                <p>为您精选的最新、最热内容</p>
                <p>{{ date }}</p>
            </div>

            {% for item in hot_items %}
            <div class="hot-item">
                <div class="item-header">
                    <h2 class="item-title">{{ item.title }}</h2>
                    <div class="hot-score">{{ item.hot_score }}</div>
                </div>

                <div class="item-category">{{ item.category }}</div>

                {% if item.description %}
                <div class="item-description">{{ item.description }}</div>
                {% endif %}

                {% if item.ai_summary %}
                <div class="item-summary">
                    <p>{{ item.ai_summary }}</p>
                </div>
                {% endif %}

                {% if item.ai_tags %}
                <div class="item-tags">
                    {% for tag in item.ai_tags %}
                    <span class="tag">{{ tag }}</span>
                    {% endfor %}
                </div>
                {% endif %}

                <div class="item-link">
                    <a href="{{ item.url }}" target="_blank">查看全文 →</a>
                </div>

                <div class="item-time">
                    发布时间: {{ item.publish_time }} | 收集时间: {{ item.collected_at }}
                </div>
            </div>
            {% endfor %}

            <div class="footer">
                <p>此邮件由 Alfred 系统自动生成</p>
                <p>© {{ year }} Alfred - 个人AI数据处理系统</p>
            </div>
        </div>
    </body>
    </html>
    """

    template = Template(html_template)
    html_content = template.render(
        hot_items=hot_items,
        date=datetime.now().strftime('%Y年%m月%d日'),
        year=datetime.now().year
    )

    return html_content


def send_email(subject: str, html_content: str, recipients: list):
    """
    发送邮件

    :param subject: 邮件主题
    :param html_content: HTML内容
    :param recipients: 收件人列表
    """
    # 从环境变量获取邮件配置
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    sender_email = os.getenv('SENDER_EMAIL', 'yueyong.lyy@icloud.com')
    sender_password = os.getenv('SENDER_PASSWORD', '')

    if not sender_email or not sender_password:
        logger.error("请在环境变量中设置SENDER_EMAIL和SENDER_PASSWORD")
        return False

    try:
        # 创建邮件对象
        message = MIMEMultipart()
        message['From'] = Header(f"Alfred系统<{sender_email}>", 'utf-8')
        message['To'] = Header(', '.join(recipients), 'utf-8')
        message['Subject'] = Header(subject, 'utf-8')

        # 添加HTML内容
        message.attach(MIMEText(html_content, 'html', 'utf-8'))

        # 连接SMTP服务器并发送邮件
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipients, message.as_string())
        server.quit()

        logger.info(f"邮件发送成功，收件人: {recipients}")
        return True
    except Exception as e:
        logger.error(f"邮件发送失败: {e}")
        return False


def main():
    """
    主函数，获取热点数据并发送邮件
    """
    logger.info("开始生成每日热点摘要邮件...")

    # 获取热点数据
    hot_items = get_top_hot_items(5)

    if not hot_items:
        logger.warning("没有获取到热点数据")
        return

    # 生成HTML内容
    html_content = generate_html_content(hot_items)

    # 从环境变量获取收件人列表
    recipients_str = os.getenv('DAILY_HOT_RECIPIENTS', '')
    if not recipients_str:
        logger.error("请在环境变量中设置DAILY_HOT_RECIPIENTS")
        return

    recipients = [email.strip() for email in recipients_str.split(',') if email.strip()]

    logger.info(f"准备发送邮件，收件人列表: {recipients}")
    # 发送邮件
    subject = f"🔥 每日热点摘要 - {datetime.now().strftime('%Y年%m月%d日')}"
    success = send_email(subject, html_content, recipients)

    if success:
        logger.info("每日热点摘要邮件发送成功")
    else:
        logger.error("每日热点摘要邮件发送失败")


if __name__ == "__main__":
    main()