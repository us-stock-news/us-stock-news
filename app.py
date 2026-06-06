import streamlit as st
import feedparser
import time
import requests
from datetime import datetime, timedelta
import google.generativeai as genai
import yfinance as yf

st.set_page_config(page_title="미국 증시 실시간 뉴스", page_icon="📈", layout="centered")

# 1. API 키 설정 및 자동 모델 감지
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
st.write("주요 지수 및 핵심 종목의 실시간 속보와 장 마감 종합 브리핑을 제공합니다.")
st.markdown("---")

# 실시간 속보를 모니터링할 관심 종목
tickers = ["QQQ", "SPY", "AAPL", "MSFT", "NVDA", "COIN"]

# 날짜 자동 계산
kst_now = datetime.utcnow() + timedelta(hours=9)
today_str = kst_now.strftime("%Y년 %m월 %d일")

# [신규 추가] 나스닥 시총 상위 10개 종목 데이터 가져오기 (종가, 등락, 등락률 계산)
@st.cache_data(ttl=1800)
def get_top10_data():
    # 나스닥 시가총액 상위 10대 테크 기업
    top10_tickers = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "AVGO", "TSLA", "COST", "NFLX"]
    data_list = []
    
    for t in top10_tickers:
        try:
            stock = yf.Ticker(t)
            # 최근 5일 데이터를 불러와 휴장일/주말 이슈 방지
            hist = stock.history(period="5d") 
            if len(hist) >= 2:
                curr_price = hist['Close'].iloc[-1]
                prev_price = hist['Close'].iloc[-2]
                change = curr_price - prev_price
                change_pct = (change / prev_price) * 100
                
                data_list.append({
                    "종목명": t,
                    "현재가": curr_price,
                    "등락": change,
                    "등락률": change_pct
                })
        except:
            pass
    return data_list

def get_crypto_price():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&contract_addresses=&vs_currencies=usd"
        response = requests.get(url, timeout=5).json()
        return response['bitcoin']['usd']
    except:
        return 61250 

@st.cache_data(ttl=600)
def get_news():
    all_news = []
    for ticker in tickers:
        try:
            url = f"https://news.google.com/rss/search?q={ticker}+news+when:1d&hl=en-US&gl=US&ceid=US:en"
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
def get_ai_summary(news_list, current_date, btc_price):
    if not model:
        return "AI 모델이 정상적으로 연결되지 않아 요약을 제공할 수 없습니다."
        
    if not news_list:
        return "뉴스를 불러오지 못했습니다."
    
    titles = [f"- [{news['ticker']}] {news['title']}" for news in news_list[:10]]
    
    prompt = f"""
    오늘은 {current_date}이야. 
    현재 가상자산 시장의 실제 비트코인(BTC) 실시간 가격은 {btc_price:,}달러 부근에서 거래되고 있어. (과거 기사 인용 금지)
    
    다음은 미국 증시 최신 영문 기사 제목들이야. 이 자료들과 현재 비트코인 시황({btc_price:,}달러선)을 바탕으로, 국내 투자자들을 위한 {current_date} 글로벌 증시 브리핑을 딱 3줄로 알기 쉽게 요약해줘. 
    시장의 주요 상승 또는 하락 원인을 명확히 포함해줘. (마크다운 불릿 포인트 활용)
    
    기사 제목 목록:
    """ + "\n".join(titles)
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"🚨 진짜 에러 원인: {str(e)}"

# 데이터 수집 실행
news_data = get_news()
current_btc_price = get_crypto_price()
top10_data = get_top10_data() # 시총 상위 10개 데이터 수집

if len(news_data) == 0:
    st.error("뉴스를 불러오고 있습니다. 잠시 후 새로고침(F5)을 눌러주세요.")
else:
    # 1. AI 3줄 브리핑 단락
    st.subheader("🤖 제미나이 AI의 현재 증시 3줄 브리핑")
    with st.info(f"✅ {today_str} 한국 시간 오전 6시 장 마감 시황 및 최근 24시간 속보를 종합 분석한 결과입니다."):
        st.markdown(get_ai_summary(news_data, today_str, current_btc_price))
    
    st.markdown("---")
    
    # 2. [완전 개편] 주요 기술주 종가 (빨강/파랑 색상 적용 표)
    st.subheader("📊 주요 기술주 종가 (나스닥 시총 상위)")
    
    if top10_data:
        # 표의 헤더 부분 생성
        html_table = """
        <table style="width:100%; border-collapse: collapse; text-align: right; font-size: 16px;">
            <thead>
                <tr style="border-bottom: 2px solid rgba(128,128,128,0.3);">
                    <th style="text-align: left; padding: 10px;">종목명</th>
                    <th style="padding: 10px;">현재가</th>
                    <th style="padding: 10px;">등락</th>
                    <th style="padding: 10px;">등락률</th>
                </tr>
            </thead>
            <tbody>
        """
        
        # 데이터 한 줄씩 넣으면서 색상 조건 부여
        for item in top10_data:
            if item['등락'] > 0:
                color = "#ff4b4b" # 상승: 빨간색
                sign = "+"
            elif item['등락'] < 0:
                color = "#1e88e5" # 하락: 파란색
                sign = ""
            else:
                color = "gray"    # 보합: 회색
                sign = ""
                
            price_str = f"${item['현재가']:,.2f}"
            change_str = f"{sign}{item['등락']:,.2f}"
            pct_str = f"{sign}{item['등락률']:.2f}%"
            
            html_table += f"""
            <tr style="border-bottom: 1px solid rgba(128,128,128,0.1);">
                <td style="text-align: left; padding: 10px; font-weight: bold;">{item['종목명']}</td>
                <td style="padding: 10px; color: {color}; font-weight: bold;">{price_str}</td>
                <td style="padding: 10px; color: {color};">{change_str}</td>
                <td style="padding: 10px; color: {color};">{pct_str}</td>
            </tr>
            """
        html_table += "</tbody></table>"
        
        # HTML 렌더링으로 스트림릿 화면에 표출
        st.markdown(html_table, unsafe_allow_html=True)
    else:
        st.warning("종가 데이터를 불러오지 못했습니다.")
        
    st.markdown("---")
    
    # 3. 뉴스 기사 단락
    for news in news_data:
        st.subheader(f"[{news['ticker']}] {news['title']}")
        st.caption(f"🕒 {news['time']} | ✍️ {news['publisher']}")
        st.markdown(f"[👉 뉴스 원문 보러가기]({news['link']})")
        st.markdown("---")
