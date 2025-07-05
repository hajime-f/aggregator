import json
import os
import re
import urllib.request
from datetime import datetime

import google.generativeai as genai
import yaml
from bs4 import BeautifulSoup
from dotenv import load_dotenv


class Aggregator:
    def __init__(self):
        self.url = "https://news.yahoo.co.jp/rss"

        load_dotenv()
        genai.configure(api_key=os.getenv("GEMINI_APIKey"))

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

                dt_object = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %Z")
                is_today = dt_object.date() == datetime.now().date()

                if is_today:
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
            try:
                content_text = soup.find_all(
                    "p",
                    class_="sc-54nboa-0 deLyrJ yjSlinkDirectlink highLightSearchTarget",
                )[0].get_text()
                content_text = content_text.replace("\u3000", " ").replace("\n", "")
                news["content"] = content_text
            except Exception:
                pass

        return list_news


if __name__ == "__main__":
    agg = Aggregator()
    list_uri = agg.fetch_uri_list()
    list_uri = list_uri[:20]
    list_news = agg.make_list_news(list_uri)
    # list_news = [
    #     {
    #         "title": "大相撲名古屋場所“東西の横綱”豊昇龍・大の里が熱田神宮で土俵入り奉納(CBCテレビ)",
    #         "link": "https://news.yahoo.co.jp/articles/20a9eb9f37a49c034952065e4cbed215c506beca?source=rss",
    #         "pubDate": "Sat, 05 Jul 2025 10:28:30 GMT",
    #     },
    #     {
    #         "title": "どこが違うの？初代フィアット・パンダは23年間で450万台を生産したロングセラー！スペイン製やバンモデルもある!?(MotorFan)",
    #         "link": "https://news.yahoo.co.jp/articles/83eb8195026bc3171f82ed0d6652f5eadd199e30?source=rss",
    #         "pubDate": "Sat, 05 Jul 2025 08:36:29 GMT",
    #     },
    #     {
    #         "title": "男性2人溺れ心肺停止、徳島 キャンプ場付近で川遊び中か(共同通信)",
    #         "link": "https://news.yahoo.co.jp/articles/65de672944f2f7bc261580806ebbedf21a9adb80?source=rss",
    #         "pubDate": "Sat, 05 Jul 2025 08:12:44 GMT",
    #     },
    #     {
    #         "title": "【王位戦】藤井聡太王位６連覇へ波乱の幕開け、指し直し局は永瀬拓矢九段が46手目を封じる(日刊スポーツ)",
    #         "link": "https://news.yahoo.co.jp/articles/6b00f53aec4a88acc876d585cd45aafacd2acfdb?source=rss",
    #         "pubDate": "Sat, 05 Jul 2025 10:17:44 GMT",
    #     },
    #     {
    #         "title": "ザポリージャ原発 一時すべての電源喪失 送電線1本の復旧を発表 ウクライナ(ABEMA TIMES)",
    #         "link": "https://news.yahoo.co.jp/articles/8821177cd2614cc7adc3b69a67409a8c9580d433?source=rss",
    #         "pubDate": "Sat, 05 Jul 2025 06:12:56 GMT",
    #     },
    #     {
    #         "title": "5日の愛知・豊田市は最高気温が37.5度と全国一番の暑さ 6日も名古屋で37度の予想など各地で猛暑日の見込み しっかりと熱中症対策を(CBCテレビ)",
    #         "link": "https://news.yahoo.co.jp/articles/685b2aae0f5c115a9b11987152b7646f30172ba8?source=rss",
    #         "pubDate": "Sat, 05 Jul 2025 10:14:36 GMT",
    #     },
    # ]
    list_news = agg.fetch_content(list_news)
    breakpoint()

    gemini = genai.GenerativeModel("gemini-1.5-flash-latest")
    prompt = f"""
    40代の男性（高学歴・高年収・コンピュータが専門・テクノロジーに強い・兵庫県西宮市在住・音楽（特に吹奏楽）が好き・資産運用に興味がある）が日々キャッチアップしておくべき情報を、次の巨大なニュースコーパスから抜き出したいと考えています。
    この目的を踏まえて、下記(1)〜(5)のアクションを実行してください。
    (1) この男性が読んでおくべきと考えられるコンテンツを抽出する。
    (2) 抽出したコンテンツを横断的に分析し、類似のコンテンツを統合した上で要約する。ただし、統合・要約した元のコンテンツが特定できるように、タイトルとURLを対応づけておく。
    (3) 30個以下のトピックに対して上記要約を準備する。ただし、これらのトピックは互いに重複がないようにする。
    (4) 準備した要約をEmacsのorg-modeで表示しやすい形式にフォーマットする。ただし、適宜改行を入れるなどの処理を行って、男性が読みやすいように工夫すること。
    (5) Pythonで処理しやすいように、JSON形式でレスポンスを返す。ただし、レスポンスにはMarkdownのコードブロックなどの余計な文字列を含めず、単純なJSONテキストのみが含まれるようにする（Pythonで読み込んでリスト型・辞書型に変換するため）。
    {list_news}
    """
    response = gemini.generate_content(prompt)
    print(response.text)

    breakpoint()
