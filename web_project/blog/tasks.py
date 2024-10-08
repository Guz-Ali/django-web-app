from django.utils import timezone
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from .models import Post
import json
import google.generativeai as genai
from newsapi import NewsApiClient

class AINewsGenerator:
    def __init__(self):
        self._get_creds()
        self._set_client()
        self._set_model()

    def _get_creds(self):
        with open("/etc/config.json") as config_file:
            config = json.load(config_file)
        self.creds = {}
        self.creds["GEMINI_API_KEY"] = config["GEMINI_API_KEY"]
        self.creds["NEWS_API_KEY"] = config["NEWS_API_KEY"]
        self.creds["PROMPT"] = config["PROMPT"]

    def _set_client(self):
        self.client = NewsApiClient(api_key=self.creds["NEWS_API_KEY"])
    
    def _set_model(self):
        genai.configure(api_key=self.creds["GEMINI_API_KEY"])
        self.model = genai.GenerativeModel("gemini-1.5-flash")

    def get_sources(self, lang="en"):
        try:
            get_sources_json = self.client.get_sources(language=lang)
            if get_sources_json["status"] != "ok":
                raise ValueError
            sources_json = get_sources_json["sources"]
            sources_arr = []
            for source in sources_json:
                sources_arr.append(source["id"])
            sources = ",".join(sources_arr)
            return sources
        except ValueError as e:
            exit(e, "API call (get_sources) status NOT OK")
    
    def get_articles(self, sources):
        try:    
            top_headlines = self.client.get_top_headlines(sources=sources)
            if top_headlines["status"] != "ok":
                raise ValueError
            articles = top_headlines["articles"]
            return articles
        except ValueError as e:
            exit(e, "API call (get_articles) status NOT OK")
    
    def prepare_prompt(self, articles):
        all_news = []
        for article in articles:
            if not (
                article["source"]["name"]
                and article["title"]
                and article["description"]
                and article["publishedAt"]
                and article["content"]
                and article["url"]
            ):
                continue
            news = []
            news.append(article["source"]["name"])
            news.append("\n")
            news.append(article["title"])
            news.append("\n")
            news.append(article["description"])
            news.append("\n")
            news.append(article["publishedAt"])
            news.append("\n")
            news.append(article["content"])
            news.append("\n")
            news.append(article["url"])
            news.append("\n\n")
            news_string = "".join(news)
            all_news.append(news_string)

        all_news.append(self.creds["PROMPT"])
        return all_news
    
    def collect_news(self):
        sources = self.get_sources()
        articles = self.get_articles(sources)
        prompt = self.prepare_prompt(articles)
        return prompt

    def generate_ai_text(self, prompt):
        response = self.model.generate_content(prompt)
        return response.text

    def create_ai_post(self, ai_news_text):
        ai_post = Post(title="Today's News",
                            content=ai_news_text,
                            date_posted=timezone.now(),
                            author = get_object_or_404(User, username="AI_NEWS"))
        ai_post.save()

