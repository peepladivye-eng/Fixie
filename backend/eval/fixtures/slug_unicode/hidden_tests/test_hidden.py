from slug import slugify
def test_unicode_letters(): assert slugify('東京 News') == '東京-news'
