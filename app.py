import streamlit as st
import feedparser
import time
import google.generativeai as genai

# 웹사이트 기본 설정
st.set_page_config(page_title="미국 증시 실시간 뉴스", page_icon="📈", layout="centered")

# 제미나이 AI 설정 (스트림릿 Secrets에서 키를 가져옴)
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

st.title("📈 미국 증시 실시간 핵심 뉴스")
st.write("주요 지수 및 기술주의 가장 빠른 영문 속보와 AI 요약을 제공합니다.")
st.markdown("---")

tickers = ["QQQ", "SPY", "AAPL", "MSFT", "NVDA", "COIN"]

@st.cache_data(ttl=600)
def get_news():
    all_news = []
    for ticker in tickers:
        try:
            url = f"https://news.google.com/rss/search?q={ticker}+stock+news&hl=en-US&gl=US&ceid=US:en"
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                parsed_time = entry.published_parsed
                if parsed_time:
                    pub_time_str = time.strftime('%Y-%m-%d %H:%M', parsed_time)
                    timestamp = time.mktime(parsed_time)
                else:
                    pub_time_str = "시간 정보 없음"
                    timestamp = 0
                
                publisher = entry.source.title if hasattr(entry, 'source') else "Google News"
                
                all_news.append({
                    "ticker": ticker,
                    "title": entry.title,
                    "publisher": publisher,
                    "link": entry.link,
                    "time": pub_time_str,
                    "timestamp": timestamp
                })
        except:
            pass
            
    all_news.sort(key=lambda x: x["timestamp"], reverse=True)
    return all_news[:30]

# AI 3줄 요약 함수 (캐싱하여 API 호출 최소화)
@st.cache_data(ttl=1800) # 요약은 30분마다 갱신
def get_ai_summary(news_list):
    if not news_list:
        return "뉴스를 불러오지 못했습니다."
    
    # 최신 뉴스 10개의 제목만 추려서 AI에게 전달
    titles = [f"- [{news['ticker']}] {news['title']}" for news in news_list[:10]]
    prompt = "다음은 현재 미국 증시 최신 영문 기사 제목들이야. 이 기사들의 흐름을 분석해서, 한국어 투자자들을 위해 현재 시장 분위기와 핵심 이슈를 딱 3줄로 알기 쉽게 요약해줘. (마크다운 불릿 포인트 활용)\n\n" + "\n".join(titles)
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return "AI 브리핑을 생성하는 중 일시적인 오류가 발생했습니다."

news_data = get_news()

if len(news_data) == 0:
    st.error("뉴스를 불러오고 있습니다. 잠시 후 새로고침(F5)을 눌러주세요.")
else:
    # 화면 최상단에 AI 요약 브리핑 박스 배치
    st.subheader("🤖 제미나이 AI의 현재 증시 3줄 브리핑")
    with st.info("방금 올라온 최신 뉴스 10개를 분석한 결과입니다."):
        st.markdown(get_ai_summary(news_data))
    
    st.markdown("---")
    
    # 그 아래에 개별 뉴스 리스트 출력
    for news in news_data:
        st.subheader(f"[{news['ticker']}] {news['title']}")
        st.caption(f"🕒 {news['time']} | ✍️ {news['publisher']}")
        st.markdown(f"[👉 뉴스 원문 보러가기]({news['link']})")
        st.markdown("---")
