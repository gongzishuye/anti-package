#!/usr/bin/env python3
"""
企业微信机器人通知模块
"""

import base64
import hashlib
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Union

import requests
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WeComNotifier:
    """企业微信机器人通知器"""
    
    def __init__(self, webhook_url: str = None):
        """
        初始化企业微信通知器
        
        Args:
            webhook_url: 企业微信机器人webhook地址
        """
        self.webhook_url = webhook_url
    
    def _send_to_webhook(self,
                         url: str,
                         content: Union[str, Dict[str, str]],
                         msgtype: str = "markdown") -> bool:
        """
        发送消息到指定webhook
        
        Args:
            url: webhook地址
            content: 消息内容
            msgtype: 消息类型（markdown或text）
            
        Returns:
            是否发送成功
        """
        try:
            data: Dict[str, Dict[str, str]] = {"msgtype": msgtype}

            if msgtype in {"markdown", "text"}:
                data[msgtype] = {"content": str(content)}
            elif msgtype == "image":
                if not isinstance(content, dict):
                    raise ValueError("Image content must be a dict with base64 and md5")
                data[msgtype] = {
                    "base64": content.get("base64", ""),
                    "md5": content.get("md5", "")
                }
            else:
                if not isinstance(content, dict):
                    raise ValueError(f"{msgtype} content must be provided as dict")
                data[msgtype] = content
            
            response = requests.post(url, json=data, timeout=10)
            result = response.json()
            
            return result.get('errcode') == 0
                
        except Exception as e:
            logger.error(f"发送消息到webhook异常: {e}")
            return False
        
    def send_text_message(self, content: str, mentioned_list: List[str] = None) -> bool:
        """
        发送文本消息
        
        Args:
            content: 消息内容
            mentioned_list: @的用户列表，如['@all']表示@所有人
            
        Returns:
            是否发送成功
        """
        if not self.webhook_url:
            logger.warning("未配置企业微信webhook地址，跳过推送")
            return False
            
        try:
            data = {
                "msgtype": "text",
                "text": {
                    "content": content
                }
            }
            
            if mentioned_list:
                data["text"]["mentioned_list"] = mentioned_list
            
            response = requests.post(self.webhook_url, json=data, timeout=10)
            result = response.json()
            
            if result.get('errcode') == 0:
                logger.info(f"✅ [企业微信] 文本消息发送成功")
                return True
            else:
                logger.error(f"❌ [企业微信] 文本消息发送失败: {result.get('errmsg')}")
                return False
                
        except Exception as e:
            logger.error(f"❌ [企业微信] 发送文本消息异常: {e}")
            return False
    
    def send_markdown_message(self, content: str) -> bool:
        """
        发送Markdown消息
        
        Args:
            content: Markdown格式的消息内容
            
        Returns:
            是否发送成功
        """
        if not self.webhook_url:
            logger.warning("未配置企业微信webhook地址，跳过推送")
            return False
        
        if self._send_to_webhook(self.webhook_url, content, msgtype="markdown"):
            logger.info(f"✅ [企业微信] Markdown消息发送成功")
            return True
        else:
            logger.error(f"❌ [企业微信] Markdown消息发送失败")
            return False
    
    def send_image_message(self,
                           image_path: Optional[str] = None,
                           image_bytes: Optional[bytes] = None) -> bool:
        """
        发送图片消息

        Args:
            image_path: 图片文件路径
            image_bytes: 图片的二进制内容

        Returns:
            是否发送成功
        """
        if not self.webhook_url:
            logger.warning("未配置企业微信webhook地址，跳过推送")
            return False

        if image_bytes is None and image_path:
            try:
                with open(image_path, "rb") as f:
                    image_bytes = f.read()
            except OSError as exc:
                logger.error(f"读取图片失败: {exc}")
                return False

        if not image_bytes:
            logger.error("未提供图片数据，无法发送")
            return False

        b64_str = base64.b64encode(image_bytes).decode("utf-8")
        md5_str = hashlib.md5(image_bytes).hexdigest()

        payload = {"base64": b64_str, "md5": md5_str}

        if self._send_to_webhook(self.webhook_url, payload, msgtype="image"):
            logger.info(f"✅ [企业微信] 图片消息发送成功")
            return True
        else:
            logger.error(f"❌ [企业微信] 图片消息发送失败")
            return False
    
    def send_fibonacci_alert(self, ticker: str, exchange: str, interval: str,
                            high: float, low: float, current_price: float,
                            retracement_level: float, retracement_price: float,
                            date: str = None) -> bool:
        """
        发送斐波那契回撤预警消息
        
        Args:
            ticker: 交易对
            exchange: 交易所
            interval: 时间周期
            high: 最高价
            low: 最低价
            current_price: 当前价格
            retracement_level: 回撤比例（如0.5表示50%）
            retracement_price: 回撤价格位置
            date: 检测日期（可选）
            
        Returns:
            是否发送成功
        """
        logger.info(f"📤 [企业微信] 开始发送斐波那契回撤预警 - {ticker} {retracement_level*100:.1f}%")
        
        # 计算价格变化
        price_change = current_price - high
        price_change_pct = (price_change / high) * 100
        
        # 构建消息内容（Markdown格式）
        date_line = f'**检测日期**: {date}\n' if date else ''
        content = f"""## 🎯 斐波那契回撤预警
        
**交易对**: {ticker}
**交易所**: {exchange.upper()}
**周期**: {interval}
{date_line}
---

**价格信息**
- 最高价: ${high:.6f}
- 最低价: ${low:.6f}
- 当前价: <font color="warning">${current_price:.6f}</font>
- 价格变化: <font color="{'warning' if price_change < 0 else 'info'}">{price_change_pct:.2f}%</font>

---

**回撤位置**
- <font color="warning">触发{retracement_level*100:.1f}%回撤位</font>
- 回撤价格: ${retracement_price:.6f}

---

**报警时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

> 提示：价格已回撤至关键斐波那契位置，请关注!
"""
        
        return self.send_markdown_message(content)


def test_wecom_notifier():
    """测试企业微信通知器"""
    import os
    
    # 从环境变量读取webhook地址
    webhook_url = os.environ.get('WECOM_WEBHOOK_URL')
    
    if not webhook_url:
        print("请设置环境变量 WECOM_WEBHOOK_URL")
        print("例如: export WECOM_WEBHOOK_URL='https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx'")
        return
    
    notifier = WeComNotifier(webhook_url)
    
    # 测试文本消息
    print("测试发送文本消息...")
    success = notifier.send_text_message("这是一条测试消息")
    print(f"文本消息发送{'成功' if success else '失败'}")
    
    # 测试斐波那契预警消息
    print("\n测试发送斐波那契回撤预警...")
    success = notifier.send_fibonacci_alert(
        ticker="BTCUSDT",
        exchange="bn",
        interval="1D",
        high=50000.0,
        low=45000.0,
        current_price=47500.0,
        retracement_level=0.5,
        retracement_price=47500.0,
        date=datetime.now().strftime('%Y-%m-%d')
    )
    print(f"预警消息发送{'成功' if success else '失败'}")


if __name__ == "__main__":
    test_wecom_notifier()

