"""
A/B测试顾问模块测试
"""
import pytest
from app.ab_test_advisor import ABTestAdvisor, ABTestVariant


def test_generate_title_variants():
    """测试标题变体生成"""
    advisor = ABTestAdvisor()
    
    original_title = "Bluetooth Speaker"
    competitor_analysis = {
        'missing_keywords': ['portable', 'wireless', 'bass'],
        'title_length_avg': 50
    }
    
    variants = advisor.generate_title_variants(original_title, competitor_analysis)
    
    assert len(variants) > 0
    assert any('portable' in v.title.lower() for v in variants)


def test_generate_bullet_variants():
    """测试bullet变体生成"""
    advisor = ABTestAdvisor()
    
    original_bullets = [
        'Great sound quality',
        'Waterproof design',
        'Long battery life'
    ]
    
    variants = advisor.generate_bullet_variants(original_bullets, {})
    
    assert len(variants) >= 2
    assert variants[0].name == 'Bullets_A_Reorder'
    assert variants[1].name == 'Bullets_B_SocialProof'


def test_generate_price_test_plan():
    """测试价格测试方案"""
    advisor = ABTestAdvisor()
    
    competitor_analysis = {
        'price_benchmark': {
            'average': 34.99,
            'min': 24.99,
            'max': 49.99
        }
    }
    
    plan = advisor.generate_price_test_plan(29.99, competitor_analysis)
    
    assert plan['current_position'] == 'below'
    assert len(plan['recommendations']) == 3
    assert plan['recommendations'][0]['variant'] == 'Price_A_Match'


def test_generate_full_test_plan():
    """测试完整测试计划"""
    advisor = ABTestAdvisor()
    
    my_listing = {
        'title': 'Bluetooth Speaker Waterproof',
        'bullets': ['Feature 1', 'Feature 2'],
        'price': 29.99
    }
    
    competitor_analysis = {
        'price_benchmark': {'average': 34.99, 'min': 24.99, 'max': 49.99},
        'missing_keywords': ['portable'],
        'title_length_avg': 60
    }
    
    plan = advisor.generate_full_test_plan(my_listing, competitor_analysis)
    
    assert 'title_tests' in plan
    assert 'bullet_tests' in plan
    assert 'price_tests' in plan
    assert 'test_sequence' in plan
    assert len(plan['test_sequence']) == 4  # 4周计划
