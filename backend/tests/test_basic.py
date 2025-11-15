"""
Basic tests for PPT Automation
"""
from core import PPTAutomation, ContentGenerator, SlidesClient


def test_content_generator():
    """Test content generation"""
    try:
        generator = ContentGenerator()
        content = generator.generate_content('TITLE', 'Test Company', profile='company')
        assert content and len(content) > 0
        print("✅ Content generator test passed")
        return True
    except Exception as e:
        print(f"❌ Content generator test failed: {e}")
        return False


def test_slides_client():
    """Test slides client initialization"""
    try:
        client = SlidesClient()
        assert client.service is not None
        print("✅ Slides client test passed")
        return True
    except Exception as e:
        print(f"❌ Slides client test failed: {e}")
        return False


def test_automation_init():
    """Test automation initialization"""
    try:
        automation = PPTAutomation(use_ai=False)  # Use fallback to avoid API requirements
        assert automation.slides_client is not None
        assert automation.content_generator is not None
        print("✅ Automation initialization test passed")
        return True
    except Exception as e:
        print(f"❌ Automation initialization test failed: {e}")
        return False


def run_all_tests():
    """Run all basic tests"""
    print("🧪 Running Basic Tests")
    print("=" * 30)
    
    tests = [
        ("Content Generator", test_content_generator),
        ("Slides Client", test_slides_client),
        ("Automation Init", test_automation_init),
    ]
    
    passed = 0
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name}...")
        if test_func():
            passed += 1
    
    print(f"\n📊 Test Results: {passed}/{len(tests)} tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    run_all_tests()
