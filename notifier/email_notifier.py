# -*- coding: utf-8 -*-
"""
邮件发送工具
支持发送纯文本和HTML格式的邮件
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from typing import List, Optional

import envUtils


def send_email(
        to_email: str,
        subject: str,
        content: str,
        content_type: str = 'plain',
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        smtp_server: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        cc_emails: Optional[List[str]] = None,
        bcc_emails: Optional[List[str]] = None,
) -> bool:
    """
    发送邮件到指定邮箱
    
    参数:
        to_email: 收件人邮箱地址（单个邮箱或逗号分隔的多个邮箱）
        subject: 邮件主题
        content: 邮件内容
        content_type: 内容类型，'plain' 为纯文本，'html' 为HTML格式，默认为 'plain'
        from_email: 发件人邮箱，必填
        from_name: 发件人名称，可选
        smtp_server: SMTP服务器地址，必填
        smtp_port: SMTP服务器端口，默认587
        smtp_user: SMTP用户名，必填
        smtp_password: SMTP密码，必填
        cc_emails: 抄送邮箱列表，可选
        bcc_emails: 密送邮箱列表，可选
    
    返回:
        bool: 发送成功返回True，失败返回False
    """
    try:
        # 设置默认值
        smtp_port = smtp_port or 587

        # 检查必要的配置
        if not smtp_server:
            raise ValueError("SMTP服务器地址未配置，请传入 smtp_server 参数")
        if not smtp_user:
            raise ValueError("SMTP用户名未配置，请传入 smtp_user 参数")
        if not smtp_password:
            raise ValueError("SMTP密码未配置，请传入 smtp_password 参数")
        if not from_email:
            raise ValueError("发件人邮箱未配置，请传入 from_email 参数")

        # 创建邮件对象
        msg = MIMEMultipart('alternative')
        # 确保邮件头中的发件人与信封发件人一致
        if from_name:
            # 使用 formataddr 确保格式正确
            from email.utils import formataddr
            msg['From'] = formataddr((from_name, from_email))
        else:
            msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = Header(subject, 'utf-8')

        # 添加抄送
        if cc_emails:
            msg['Cc'] = ', '.join(cc_emails)

        # 添加邮件正文
        if content_type.lower() == 'html':
            msg.attach(MIMEText(content, 'html', 'utf-8'))
        else:
            msg.attach(MIMEText(content, 'plain', 'utf-8'))

        # 准备收件人列表（包括抄送和密送）
        recipients = [email.strip() for email in to_email.split(',')]
        if cc_emails:
            recipients.extend([email.strip() for email in cc_emails])
        if bcc_emails:
            recipients.extend([email.strip() for email in bcc_emails])

        # 连接SMTP服务器并发送邮件
        # 根据端口选择使用SSL或普通连接
        if smtp_port == 465:
            # 使用SSL连接（465端口）
            with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
                server.login(smtp_user, smtp_password)
                # 信封发件人必须与邮件头中的发件人一致
                server.sendmail(from_email, recipients, msg.as_string())
        else:
            # 普通连接（587端口或其他端口）
            # 某些服务器不支持STARTTLS，直接连接
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                # 尝试使用STARTTLS，如果服务器不支持则跳过
                try:
                    server.starttls()
                except smtplib.SMTPNotSupportedError:
                    # 服务器不支持STARTTLS，继续使用普通连接
                    pass
                server.login(smtp_user, smtp_password)
                # 信封发件人必须与邮件头中的发件人一致
                server.sendmail(from_email, recipients, msg.as_string())

        print(f"邮件发送成功！收件人: {to_email}")
        return True

    except smtplib.SMTPException as e:
        print(f"SMTP错误: {str(e)}")
        return False
    except Exception as e:
        print(f"发送邮件失败: {str(e)}")
        return False


# 给我自己发邮件
def send_to_myself(subject: str, from_name: str, html_content: str):
    return send_email(
        to_email='475643653@qq.com',
        subject=subject,
        content=html_content,
        content_type='html',
        from_name=from_name,
        from_email='grjelf@sina.com',
        smtp_port=465,  # 使用465端口（SSL），如果不行可以尝试587
        smtp_server='smtp.sina.com',
        smtp_user='grjelf@sina.com',  # SMTP用户名应该是完整的邮箱地址
        smtp_password=envUtils.email_sina_pwd,
    )


if __name__ == '__main__':
    html_content = """
    <html>
    <body>
        <h2>测试邮件</h2>
        <p>这是一封HTML格式的测试邮件。</p>
        <p>如果您看到这段内容，说明邮件发送功能正常工作。</p>
        <p style="color: #666; font-size: 12px;">自动化市场分析系统</p>
    </body>
    </html>
    """
    result = send_to_myself(
        subject='测试',
        from_name='NewsDistill',
        html_content=html_content
    )
    if result:
        print("测试邮件发送成功！")
    else:
        print("测试邮件发送失败！")
