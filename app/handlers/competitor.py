"""
竞品分析命令处理器
"""
from telegram import Update
from telegram.ext import ContextTypes
from app.competitor_analyzer import CompetitorAnalyzer
from app.ab_test_advisor import ABTestAdvisor


async def handle_competitor_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /competitor <url1> <url2> <url3>
    分析竞品并生成对比报告
    """
    if not context.args:
        await update.message.reply_text(
            "用法: /competitor <url1> [url2] [url3]\n"
            "支持平台: Amazon ASIN, Shopee链接\n"
            "示例: /competitor B08XYZ123 https://shopee.sg/product/123/456"
        )
        return
    
    await update.message.reply_text("🔍 正在分析竞品...")
    
    analyzer = CompetitorAnalyzer()
    competitors = []
    
    for url_or_asin in context.args[:5]:  # 最多5个竞品
        try:
            if url_or_asin.startswith('http'):
                if 'shopee' in url_or_asin:
                    comp = await analyzer.analyze_shopee_url(url_or_asin)
                else:
                    await update.message.reply_text(f"⚠️ 暂不支持该平台: {url_or_asin}")
                    continue
            else:
                # 假设是Amazon ASIN
                comp = await analyzer.analyze_amazon_asin(url_or_asin)
            
            competitors.append(comp)
        except Exception as e:
            await update.message.reply_text(f"❌ 分析失败 {url_or_asin}: {str(e)}")
    
    if not competitors:
        await update.message.reply_text("❌ 没有成功分析任何竞品")
        return
    
    # 生成对比报告
    report = f"📊 **竞品分析报告** ({len(competitors)}个竞品)\n\n"
    
    for i, comp in enumerate(competitors, 1):
        report += f"**竞品 {i}** - {comp.platform}\n"
        report += f"标题: {comp.title[:60]}...\n"
        report += f"价格: ${comp.price:.2f} | 评分: {comp.rating}⭐ ({comp.reviews_count} reviews)\n"
        report += f"关键词: {', '.join(comp.keywords[:8])}\n\n"
    
    # 基准数据
    avg_price = sum(c.price for c in competitors if c.price) / len([c for c in competitors if c.price])
    avg_rating = sum(c.rating for c in competitors if c.rating) / len([c for c in competitors if c.rating])
    
    report += "📈 **市场基准**\n"
    report += f"平均价格: ${avg_price:.2f}\n"
    report += f"平均评分: {avg_rating:.2f}⭐\n"
    report += f"总评论数: {sum(c.reviews_count or 0 for c in competitors)}\n\n"
    
    # 高频关键词
    all_keywords = {}
    for comp in competitors:
        for kw in comp.keywords:
            all_keywords[kw] = all_keywords.get(kw, 0) + 1
    
    top_keywords = sorted(all_keywords.items(), key=lambda x: x[1], reverse=True)[:15]
    report += "🔑 **高频关键词TOP15**\n"
    report += ', '.join([f"{kw}({cnt})" for kw, cnt in top_keywords])
    
    await update.message.reply_text(report, parse_mode='Markdown')


async def handle_abtest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /abtest
    基于最近一次竞品分析生成A/B测试方案
    """
    # 这里需要从历史记录中获取最近的listing和竞品分析
    # 简化版：使用示例数据
    
    my_listing = {
        'title': 'Portable Bluetooth Speaker Waterproof Wireless',
        'bullets': [
            '360° Surround Sound',
            'IPX7 Waterproof',
            '24H Battery Life',
            'USB-C Fast Charging',
            'Built-in Microphone'
        ],
        'price': 29.99
    }
    
    competitor_analysis = {
        'price_benchmark': {'average': 34.99, 'min': 24.99, 'max': 49.99},
        'rating_benchmark': 4.5,
        'missing_keywords': ['portable', 'outdoor', 'bass'],
        'title_length_avg': 80
    }
    
    advisor = ABTestAdvisor()
    test_plan = advisor.generate_full_test_plan(my_listing, competitor_analysis)
    
    report = "🧪 **A/B测试方案**\n\n"
    
    # 标题测试
    report += "**📝 标题优化测试**\n"
    for variant in test_plan['title_tests']:
        report += f"• {variant.name}\n"
        report += f"  标题: {variant.title}\n"
        report += f"  假设: {variant.hypothesis}\n"
        report += f"  预期: {variant.expected_impact}\n\n"
    
    # Bullet测试
    report += "**📋 Bullet优化测试**\n"
    for variant in test_plan['bullet_tests']:
        report += f"• {variant.name}\n"
        report += f"  假设: {variant.hypothesis}\n"
        report += f"  预期: {variant.expected_impact}\n\n"
    
    # 价格测试
    report += "**💰 价格测试方案**\n"
    for rec in test_plan['price_tests']['recommendations']:
        report += f"• {rec['variant']}: ${rec['price']}\n"
        report += f"  {rec['hypothesis']}\n"
        report += f"  时长: {rec['duration']} | 流量: {rec['traffic_split']}\n\n"
    
    # 测试时间表
    report += "**📅 4周测试时间表**\n"
    for week in test_plan['test_sequence']:
        report += f"Week {week['week']}: {week['focus']} ({week['variants']} variants)\n"
    
    await update.message.reply_text(report, parse_mode='Markdown')
