class HomePage():
    def __init__(self, page):
        self.page = page

    def search_product(self, keyword: str):
        self.page.fill("input[name='keyword']", keyword)
        self.page.press("input[name='keyword']", "Enter")