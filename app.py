import streamlit as st
import feedparser
import time
import google.generativeai as genai

# 웹사이트 기본 설정
st.set_page_config(page_title="미국 증시 실시간 뉴스", page_icon="📈", layout="centered")

# 1. API 키 설정 및 사용 가능한 모델 '자동 감지' (404 에러 원천 차단)
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    
    available_model = None
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            available_model = m.name
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
st.write("주요 지수 및 핵심 종목의 실시간 속보와 한국 시간 오전 6시 장 마감 종합 브리핑을 제공합니다.")
st.markdown("---")

# 모니터링할 핵심 종목 풀
tickers = ["QQQ", "SPY", "AAPL", "MSFT", "NVDA", "COIN"]

@st.cache_data(ttl=600) # 뉴스 목록은 10분마다 새로고침하여 속보성 유지
def get_news():
    all_news = []
    for ticker in tickers:
        try:
            # 장 마감(오전 6시) 전후의 마감 종합 기사(close, wrap, summary)와 핵심 뉴스를 포괄하여 수집
            url = url = f"https://news.google.com/rss/search?q={ticker}+news+when:1d&hl=en-US&gl=US&ceid=US:en"
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

@st.cache_data(ttl=1800) # AI 요약 브리핑은 30분마다 갱신
def get_ai_summary(news_list):
    if not model:
        return "AI 모델이 정상적으로 연결되지 않아 요약을 제공할 수 없습니다."
        
    if not news_list:
        return "뉴스를 불러오지 못했습니다."
    
    titles = [f"- [{news['ticker']}] {news['title']}" for news in news_list[:10]]
    
    # 오전 6시 마감 시황을 관통하는 명확한 요약 지침을 프롬프트에 주입
    prompt = "다음은 미국 증시 최신 시황 및 마감 관련 영문 기사 제목들이야. 이 자료를 바탕으로 한국 시간 오전 6시 장 마감 종합 결과를 반영하여, 국내 투자자들을 위한 글로벌 증시 브리핑을 딱 3줄로 알기 쉽게 요약해줘. 시장의 주요 상승 또는 하락 원인을 명확히 포함해줘. (마크다운 불릿 포인트 활용)\n\n" + "\n".join(titles)
    
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
    # 최상단 AI 종합 브리핑 영역
    st.subheader("🤖 제미나이 AI의 현재 증시 3줄 브리핑")
    with st.info("한국 시간 오전 6시 장 마감 시황 및 실시간 속보를 종합 분석한 결과입니다."):
        st.markdown(get_ai_summary(news_data))
    
    st.markdown("---")
    
    # 개별 뉴스 타임라인 영역
    for news in news_data:
        st.subheader(f"[{news['ticker']}] {news['title']}")
        st.caption(f"🕒 {news['time']} | ✍️ {news['publisher']}")
        st.markdown(f"[👉 뉴스 원문 보러가기]({news['link']})")
        st.markdown("---")
