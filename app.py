import streamlit as st
import feedparser
import time
import google.generativeai as genai

st.set_page_config(page_title="미국 증시 실시간 뉴스", page_icon="📈", layout="centered")

# 1. API 키 설정 및 사용 가능한 모델 '자동 감지' 로직 (404 에러 원천 차단)
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    
    # 내 계정에서 쓸 수 있는 모델 리스트를 쭉 스캔합니다.
    available_model = None
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            available_model = m.name
            # 가장 빠르고 최신인 flash 모델이 있다면 그것을 최우선으로 잡습니다.
            if 'flash' in m.name.lower():
                break
                
    if available_model:
        model = genai.GenerativeModel(available_model)
    else:
        st.error("🚨 구글 계정에 텍스트 생성이 가능한 AI 모델이 활성화되어 있지 않습니다.")
        model = None
        
except Exception as e:
    st.error(f"🚨 API 설정 에러: {e}")
    model = None

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

@st.cache_data(ttl=1800)
def get_ai_summary(news_list):
    if not model:
        return "AI 모델이 정상적으로 연결되지 않아 요약을 제공할 수 없습니다."
        
    if not news_list:
        return "뉴스를 불러오지 못했습니다."
    
    titles = [f"- [{news['ticker']}] {news['title']}" for news in news_list[:10]]
    prompt = "다음은 현재 미국 증시 최신 영문 기사 제목들이야. 이 기사들의 흐름을 분석해서, 한국어 투자자들을 위해 현재 시장 분위기와 핵심 이슈를 딱 3줄로 알기 쉽게 요약해줘. (마크다운 불릿 포인트 활용)\n\n" + "\n".join(titles)
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"🚨 진짜 에러 원인: {str(e)}"

# 뉴스 데이터 불러오기 및 화면 출력
news_data = get_news()

if len(news_data) == 0:
    st.error("뉴스를 불러오고 있습니다. 잠시 후 새로고침(F5)을 눌러주세요.")
else:
    st.subheader("🤖 제미나이 AI의 현재 증시 3줄 브리핑")
    with st.info("방금 올라온 최신 뉴스 10개를 분석한 결과입니다."):
        st.markdown(get_ai_summary(news_data))
    
    st.markdown("---")
    
    for news in news_data:
        st.subheader(f"[{news['ticker']}] {news['title']}")
        st.caption(f"🕒 {news['time']} | ✍️ {news['publisher']}")
        st.markdown(f"[👉 뉴스 원문 보러가기]({news['link']})")
        st.markdown("---")
