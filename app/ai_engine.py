"""AI generation engine with retry logic."""
import requests
import time
from app.config import config


def call_ai(
    prompt: str,
    system_msg: str = "You are an expert e-commerce copywriter and SEO specialist.",
    retries: int = 3,
) -> str:
    """Call OpenAI-compatible API with retry logic."""
    headers = {
        "Authorization": f"Bearer {config.OPENAI_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "model": config.OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt},
        ],
        "temperature": config.AI_TEMPERATURE,
        "max_tokens": config.AI_MAX_TOKENS,
    }

    last_err = None
    for attempt in range(retries):
        try:
            r = requests.post(
                f"{config.OPENAI_BASE}/chat/completions",
                headers=headers,
                json=data,
                timeout=90,
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except requests.exceptions.Timeout:
            last_err = "请求超时"
            time.sleep(2 ** attempt)
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else 0
            if status == 429:
                last_err = "API限流，稍后重试"
                time.sleep(5 * (attempt + 1))
            elif status >= 500:
                last_err = f"API服务器错误 ({status})"
                time.sleep(2 ** attempt)
            else:
                return f"⚠️ AI生成失败: HTTP {status}"
        except Exception as e:
            last_err = str(e)
            time.sleep(2 ** attempt)

    return f"⚠️ AI生成失败 (重试{retries}次): {last_err}"


def optimize_listing(original: str, platform_name: str) -> str:
    """Optimize an existing listing with AI suggestions."""
    prompt = f"""Review and optimize this {platform_name} product listing.
Provide specific improvements for:
1. SEO keyword density
2. Conversion-focused language
3. Missing elements
4. Competitor differentiation

Original listing:
{original}

Output: Optimized version + change summary."""
    return call_ai(prompt)


def translate_listing(listing: str, target_lang: str) -> str:
    """Translate a listing to another language while preserving SEO structure."""
    prompt = f"""Translate this product listing to {target_lang}.
Preserve all formatting, SEO structure, and marketing tone.
Adapt cultural references and idioms for the target market.

{listing}"""
    return call_ai(prompt)
