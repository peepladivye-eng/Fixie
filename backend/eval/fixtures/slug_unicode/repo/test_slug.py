from slug import slugify
def test_accent(): assert slugify('Café Menu') == 'café-menu'
