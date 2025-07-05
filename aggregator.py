import html
import json
import os
import re
import time
import urllib.request
from datetime import datetime

import google.generativeai as genai
import requests
import yaml
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait


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

        breakpoint()
        return dict_content

    def process_items(self, items, dict_content, key):
        for item in items:
            title = item.find("title").get_text()
            link = item.find("link").get_text()

            try:
                pub_date = item.find("pubDate").get_text()
            except AttributeError:
                pub_date = item.find("dc:date").get_text()

            try:
                dt_object = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %Z")
            except ValueError:
                try:
                    dt_object = datetime.strptime(
                        pub_date, "%a, %d %b %Y %H:%M:%S +0000"
                    )
                except ValueError:
                    dt_object = datetime.fromisoformat(pub_date)
            is_today = dt_object.date() == datetime.now().date()

            if is_today:
                if key in ("Yahoo"):
                    content = self.fetch_content_yahoo(link)
                elif key in ("橘玲", "トーマス", "Books"):
                    html_inside = item.find("content:encoded").text
                    inner_soup = BeautifulSoup(
                        html.unescape(html_inside), "html.parser"
                    )
                    plain_text = inner_soup.get_text(separator="\n", strip=True)
                    content = plain_text.replace("\n", "").replace("\u3000", " ")
                elif key in ("朝日新聞"):
                    content = self.fetch_content_asahi(link)
                elif key in ("読売新聞"):
                    content = self.fetch_content_yomiuri(link)
                elif key in ("みんかぶ"):
                    content = self.fetch_content_minkabu(link)

                news_item = {
                    "title": title.replace("\u3000", " "),
                    "link": link,
                    "pubDate": dt_object.strftime("%Y-%m-%d %H:%M"),
                    "content": content,
                }
                dict_content[key].append(news_item)

        return dict_content

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
        p_tags = soup.find("div", class_="nfyQp").find_all("p")
        text_list = [p.get_text(strip=True) for p in p_tags]
        full_text = "".join(text_list)

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
            news["content"] = content_text
        except Exception:
            pass

        return content_text


if __name__ == "__main__":
    agg = Aggregator()

    dict_sites = agg.fetch_sites()
    dict_content = agg.make_content(dict_sites)

    breakpoint()

    gemini = genai.GenerativeModel("gemini-1.5-flash-latest")
    prompt = f"""
    40代の男性（高学歴・高年収・コンピュータが専門・テクノロジーに強い・兵庫県西宮市在住・音楽（特に吹奏楽）が好き・資産運用に興味がある）が日々キャッチアップしておくべき情報を、次の巨大なニュースコーパスから抜き出したいと考えています。
    この目的を踏まえて、下記(1)〜(5)のアクションを実行してください。
    (1) この男性が読んでおくべきと考えられるコンテンツを抽出する。読んでおく必要がないと判断したコンテンツは捨てて構わない。
    (2) 抽出したコンテンツを横断的に分析し、類似のコンテンツを統合した上で要約する。ただし、統合・要約した元のコンテンツが特定できるように、タイトルとURLを対応づけておく。
    (3) 30個以下のトピックに対して上記要約を準備する。ただし、これらのトピックは互いに重複がないようにする。
    (4) 準備した要約をEmacsのorg-modeで表示しやすい形式にフォーマットする。ただし、適宜改行を入れるなどの処理を行って、男性が読みやすいように工夫すること。
    (5) Pythonで処理しやすいように、JSON形式でレスポンスを返す。ただし、レスポンスにはMarkdownのコードブロックなどの余計な文字列を含めず、単純なJSONテキストのみが含まれるようにする（Pythonで読み込んでリスト型・辞書型に変換するため）。
    {dict_content}
    """
    response = gemini.generate_content(prompt)
    print(response.text)

    breakpoint()
