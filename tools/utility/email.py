"""Email sending tool using SMTP."""

from __future__ import annotations

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict

from qwen_agent.tools.base import register_tool
from tools.core.base import QwenAgentBaseTool
from tools.core.utils import dump


@register_tool("send_email")
class SendEmailTool(QwenAgentBaseTool):
    description = "发送电子邮件，支持HTML和纯文本格式。需要配置SMTP服务器信息。"
    parameters = {
        "type": "object",
        "properties": {
            "to_email": {
                "type": "string",
                "description": "收件人邮箱地址，必填"
            },
            "subject": {
                "type": "string",
                "description": "邮件主题，必填"
            },
            "body": {
                "type": "string",
                "description": "邮件正文内容，必填"
            },
            "body_type": {
                "type": "string",
                "description": "邮件正文类型，可选值：'plain'（纯文本）或 'html'（HTML格式），默认为 'plain'",
                "enum": ["plain", "html"]
            },
            "cc": {
                "type": "string",
                "description": "抄送邮箱地址，多个邮箱用逗号分隔，可选"
            },
            "bcc": {
                "type": "string",
                "description": "密送邮箱地址，多个邮箱用逗号分隔，可选"
            }
        },
        "required": ["to_email", "subject", "body"],
    }

    def _execute_tool(self, params: Dict[str, Any], **_: Any) -> str:
        args = self._verify_json_format_args(params)
        
        # 获取必需参数
        to_email = args.get("to_email")
        subject = args.get("subject")
        body = args.get("body")
        body_type = args.get("body_type", "plain")
        cc = args.get("cc", "")
        bcc = args.get("bcc", "")
        
        # 验证必需参数
        if not to_email or not subject or not body:
            return dump({
                "task": "send_email",
                "status": "error",
                "error": "缺少必需参数：to_email, subject, body"
            })
        
        # 从环境变量读取SMTP配置
        smtp_server = os.environ.get("SMTP_SERVER")
        smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        smtp_user = os.environ.get("SMTP_USER")
        smtp_password = os.environ.get("SMTP_PASSWORD")
        from_email = os.environ.get("FROM_EMAIL", smtp_user)
        
        # 验证SMTP配置
        if not all([smtp_server, smtp_user, smtp_password]):
            return dump({
                "task": "send_email",
                "status": "error",
                "error": "SMTP配置不完整，请设置环境变量：SMTP_SERVER, SMTP_USER, SMTP_PASSWORD"
            })
        
        try:
            # 发送邮件
            result = _send_email(
                smtp_server=smtp_server,
                smtp_port=smtp_port,
                smtp_user=smtp_user,
                smtp_password=smtp_password,
                from_email=from_email,
                to_email=to_email,
                subject=subject,
                body=body,
                body_type=body_type,
                cc=cc,
                bcc=bcc
            )
            return dump(result)
        except Exception as e:
            return dump({
                "task": "send_email",
                "status": "error",
                "error": f"发送邮件失败: {str(e)}"
            })


def _send_email(
    smtp_server: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    from_email: str,
    to_email: str,
    subject: str,
    body: str,
    body_type: str = "plain",
    cc: str = "",
    bcc: str = ""
) -> Dict:
    """
    发送邮件的核心函数
    
    Args:
        smtp_server: SMTP服务器地址
        smtp_port: SMTP服务器端口
        smtp_user: SMTP用户名
        smtp_password: SMTP密码
        from_email: 发件人邮箱
        to_email: 收件人邮箱
        subject: 邮件主题
        body: 邮件正文
        body_type: 邮件正文类型（'plain' 或 'html'）
        cc: 抄送邮箱，多个用逗号分隔
        bcc: 密送邮箱，多个用逗号分隔
    
    Returns:
        包含发送结果的字典
    """
    try:
        # 创建邮件对象
        msg = MIMEMultipart("alternative")
        msg["From"] = from_email
        msg["To"] = to_email
        msg["Subject"] = subject
        
        # 添加抄送和密送
        if cc:
            msg["Cc"] = cc
        if bcc:
            msg["Bcc"] = bcc
        
        # 添加邮件正文
        if body_type == "html":
            msg.attach(MIMEText(body, "html", "utf-8"))
        else:
            msg.attach(MIMEText(body, "plain", "utf-8"))
        
        # 准备收件人列表
        recipients = [to_email]
        if cc:
            recipients.extend([email.strip() for email in cc.split(",") if email.strip()])
        if bcc:
            recipients.extend([email.strip() for email in bcc.split(",") if email.strip()])
        
        # 连接SMTP服务器并发送邮件
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # 启用TLS加密
            server.login(smtp_user, smtp_password)
            server.send_message(msg, from_addr=from_email, to_addrs=recipients)
        
        return {
            "task": "send_email",
            "status": "ok",
            "message": f"邮件已成功发送到 {to_email}",
            "recipients_count": len(recipients)
        }
        
    except smtplib.SMTPAuthenticationError:
        return {
            "task": "send_email",
            "status": "error",
            "error": "SMTP认证失败，请检查用户名和密码"
        }
    except smtplib.SMTPException as e:
        return {
            "task": "send_email",
            "status": "error",
            "error": f"SMTP错误: {str(e)}"
        }
    except Exception as e:
        return {
            "task": "send_email",
            "status": "error",
            "error": f"发送失败: {str(e)}"
        }
