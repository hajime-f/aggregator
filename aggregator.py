import re
import urllib.request

import yaml
from bs4 import BeautifulSoup


class Aggregator:
    def __init__(self):
        self.url = "https://news.yahoo.co.jp/rss"

    def fetch_uri_list(self):
        req = urllib.request.Request(self.url, method="GET")
        with urllib.request.urlopen(req) as res:
            content = res.read().decode("utf-8")
        soup = BeautifulSoup(content, "html.parser")

        tags = soup.find_all(href=re.compile("xml"))
        list_uri = []
        for t in tags:
            list_uri.append(f"https://news.yahoo.co.jp/{t.get('href')}")

        return list_uri

    def make_list_news(self, list_uri):
        list_news = []

        for uri in list_uri:
            req = urllib.request.Request(uri, method="GET")
            with urllib.request.urlopen(req) as res:
                content = res.read().decode("utf-8")
            soup = BeautifulSoup(content, "xml")
            items = soup.find_all("item")

            for item in items:
                title = item.find("title").get_text()
                link = item.find("link").get_text()
                pub_date = item.find("pubDate").get_text()

                news_item = {
                    "title": title.replace("\u3000", " "),
                    "link": link,
                    "pubDate": pub_date,
                }
                list_news.append(news_item)

        return list_news

    def fetch_content(self, list_news):
        for news in list_news:
            req = urllib.request.Request(news["link"], method="GET")
            with urllib.request.urlopen(req) as res:
                content = res.read().decode("utf-8")
            soup = BeautifulSoup(content, "html.parser")
            content_text = soup.find_all(
                "p",
                class_="sc-54nboa-0 deLyrJ yjSlinkDirectlink highLightSearchTarget",
            )[0].get_text()
            content_text = content_text.replace("\u3000", " ").replace("\n", "")
            news["content"] = content_text

        return list_news


if __name__ == "__main__":
    agg = Aggregator()
    # list_uri = agg.fetch_uri_list()
    # list_news = agg.make_list_news(list_uri)
    list_news = [
        {
            "title": "大相撲名古屋場所“東西の横綱”豊昇龍・大の里が熱田神宮で土俵入り奉納(CBCテレビ)",
            "link": "https://news.yahoo.co.jp/articles/20a9eb9f37a49c034952065e4cbed215c506beca?source=rss",
            "pubDate": "Sat, 05 Jul 2025 10:28:30 GMT",
        },
        {
            "title": "どこが違うの？初代フィアット・パンダは23年間で450万台を生産したロングセラー！スペイン製やバンモデルもある!?(MotorFan)",
            "link": "https://news.yahoo.co.jp/articles/83eb8195026bc3171f82ed0d6652f5eadd199e30?source=rss",
            "pubDate": "Sat, 05 Jul 2025 08:36:29 GMT",
        },
        {
            "title": "男性2人溺れ心肺停止、徳島 キャンプ場付近で川遊び中か(共同通信)",
            "link": "https://news.yahoo.co.jp/articles/65de672944f2f7bc261580806ebbedf21a9adb80?source=rss",
            "pubDate": "Sat, 05 Jul 2025 08:12:44 GMT",
        },
        {
            "title": "【王位戦】藤井聡太王位６連覇へ波乱の幕開け、指し直し局は永瀬拓矢九段が46手目を封じる(日刊スポーツ)",
            "link": "https://news.yahoo.co.jp/articles/6b00f53aec4a88acc876d585cd45aafacd2acfdb?source=rss",
            "pubDate": "Sat, 05 Jul 2025 10:17:44 GMT",
        },
        {
            "title": "ザポリージャ原発 一時すべての電源喪失 送電線1本の復旧を発表 ウクライナ(ABEMA TIMES)",
            "link": "https://news.yahoo.co.jp/articles/8821177cd2614cc7adc3b69a67409a8c9580d433?source=rss",
            "pubDate": "Sat, 05 Jul 2025 06:12:56 GMT",
        },
        {
            "title": "5日の愛知・豊田市は最高気温が37.5度と全国一番の暑さ 6日も名古屋で37度の予想など各地で猛暑日の見込み しっかりと熱中症対策を(CBCテレビ)",
            "link": "https://news.yahoo.co.jp/articles/685b2aae0f5c115a9b11987152b7646f30172ba8?source=rss",
            "pubDate": "Sat, 05 Jul 2025 10:14:36 GMT",
        },
    ]
    list_news = agg.fetch_content(list_news)
    breakpoint()
