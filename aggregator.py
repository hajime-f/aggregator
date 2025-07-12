import html
import json
import os
import urllib.request
from datetime import datetime, timedelta

import google.generativeai as genai
import yaml
from bs4 import BeautifulSoup
from dotenv import load_dotenv


class Aggregator:
    def __init__(self):
        load_dotenv()
        genai.configure(api_key=os.getenv("GEMINI_APIKey"))

    def fetch_sites(self):
        with open("sites.yaml", "rt") as f:
            dict_sites = yaml.safe_load(f.read())

        return dict_sites

    def request_content(self, url):
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req) as res:
            content = res.read().decode("utf-8")
        return content

    def make_content(self, dict_sites):
        dict_content = {}

        for key, sites in dict_sites.items():
            dict_content[key] = []
            for uri in sites.values():
                content = self.request_content(uri)
                soup = BeautifulSoup(content, "xml")
                items = soup.find_all("item")
                dict_content = self.process_items(items, dict_content, key)

        return dict_content

    def process_items(self, items, dict_content, key):
        for item in items:
            title = item.find("title").get_text()
            link = item.find("link").get_text()

            try:
                pub_date = item.find("pubDate").get_text()
            except AttributeError:
                pub_date = item.find("dc:date").get_text()

            if key in ("Yahoo"):
                content = self.fetch_content_yahoo(link)
            elif key in ("橘玲", "トーマス", "Books", "パレオ"):
                content = self.fetch_content_others(item, pub_date)
                if content is None:
                    continue
            elif key in ("朝日新聞"):
                content = self.fetch_content_asahi(link)
            elif key in ("読売新聞"):
                content = self.fetch_content_yomiuri(link)
            elif key in ("みんかぶ"):
                content = self.fetch_content_minkabu(link)
            elif key in ("WIRED"):
                content = self.fetch_content_wired(link)
            elif key in ("CNN"):
                content = self.fetch_content_cnn(link)

            news_item = {
                "title": title.replace("\u3000", " "),
                "link": link,
                "pubDate": pub_date,
                "content": content,
                "source": key,
            }
            dict_content[key].append(news_item)

        return dict_content

    def fetch_content_cnn(self, link):
        content = self.request_content(link)
        soup = BeautifulSoup(content, "html.parser")
        try:
            content_text = soup.find("article").find("div", id="leaf-body").get_text()
        except Exception:
            content_text = ""
        return content_text.replace("\n", "")

    def fetch_content_others(self, item, pub_date):
        target_date = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S +0000").date()
        today = datetime.now().date()
        limit_date = today - timedelta(days=1)
        is_today = limit_date <= target_date <= today

        if is_today:
            try:
                html_inside = item.find("content:encoded").text
            except AttributeError:
                html_inside = item.find("description").text
            inner_soup = BeautifulSoup(html.unescape(html_inside), "html.parser")
            plain_text = inner_soup.get_text(separator="\n", strip=True)
            content = plain_text.replace("\n", "").replace("\u3000", " ")
            return content
        else:
            return None

    def fetch_content_wired(self, link):
        content = self.request_content(link)
        soup = BeautifulSoup(content, "html.parser")
        content_list = soup.find_all("div", class_="body__inner-container")
        full_text = ""
        for content in content_list:
            full_text += content.get_text()

        return full_text

    def fetch_content_minkabu(self, link):
        content = self.request_content(link)
        soup = BeautifulSoup(content, "html.parser")
        return soup.find("p", class_="news__text mt20").get_text()

    def fetch_content_yomiuri(self, link):
        content = self.request_content(link)
        soup = BeautifulSoup(content, "html.parser")
        p_tags = soup.find("div", class_="p-main-contents").find_all(
            "p", itemprop="articleBody"
        )
        text_list = [p.get_text(strip=True) for p in p_tags]
        full_text = "".join(text_list)

        return full_text

    def fetch_content_asahi(self, link):
        content = self.request_content(link)
        soup = BeautifulSoup(content, "html.parser")

        try:
            p_tags = soup.find("div", class_="nfyQp").find_all("p")
            text_list = [p.get_text(strip=True) for p in p_tags]
            full_text = "".join(text_list)
        except AttributeError:
            full_text = ""

        return full_text

    def fetch_content_yahoo(self, link):
        content = self.request_content(link)
        soup = BeautifulSoup(content, "html.parser")
        try:
            content_text = soup.find_all(
                "p",
                class_="sc-54nboa-0 deLyrJ yjSlinkDirectlink highLightSearchTarget",
            )[0].get_text()
            content_text = content_text.replace("\u3000", " ").replace("\n", "")
        except Exception:
            pass

        return content_text


if __name__ == "__main__":
    agg = Aggregator()

    dict_sites = agg.fetch_sites()
    dict_content = agg.make_content(dict_sites)

    # json_content = json.dumps(dict_content, ensure_ascii=False)
    # with open("test.json", "w") as f:
    #     f.write(json_content)
    # with open("test.json", "r") as f:
    #     dict_content = json.load(f)

    gemini = genai.GenerativeModel("gemini-1.5-flash-latest")
    prompt = f"""
    40代の日本人男性（コンピュータが専門・テクノロジーに強い・兵庫県西宮市在住・音楽（特に吹奏楽）が好き・資産運用に興味がある）が日々キャッチアップしておくべき情報を、次の巨大なニュースコーパスから抜き出したいと考えています。この目的を踏まえて、下記(1)〜(4)のアクションを実行してください。
    (1) この男性が読んでおくべきと考えられるコンテンツを抽出する。なお、読んでおく必要がないと判断したコンテンツは積極的に捨てて構わない。
    (2) 抽出したコンテンツを横断的に分析し、類似のコンテンツを統合した上で、日本語で要約する。ただし、統合・要約した元のコンテンツが特定できるように、タイトルとURLを対応づけておく。また、タイトルだけ抜き出した浅い要約にならないようにすること。
    (3) 30個以下のトピックに対して上記日本語の要約を準備する。ただし、これらのトピックは互いに重複がないようにすること。また、各トピックの要約は、500〜700文字程度とし、タイトルの列挙ではなく、内容を掘り下げた要約にすること。
    (4) Pythonで処理しやすいように、JSON形式でレスポンスを返す。ただし、このレスポンスにはMarkdownのコードブロックなどの余計な文字列を含めてはならない。
    {dict_content}
    """
    response_text = gemini.generate_content(prompt).text

    with open("format.txt", "r") as f:
        format_text = f.read()

    prompt = f"""
    次のフォーマットに則って下記のテキストを整形してください。レスポンスにはMarkdownのコードブロックなどの余計な文字列を含めないでください。
    {format_text}
    {response_text}
    """
    response_text2 = gemini.generate_content(prompt).text

    attr = datetime.now().date().strftime("%Y-%m-%d")
    file_name = f"./news/{attr}_本日のニュース.org"

    with open(file_name, "w") as f:
        f.write(response_text2)
