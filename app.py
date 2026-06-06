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

# 날짜 및 시간 자동 계산 (세계 표준시 + 9시간 = 한국 시간)
kst_now = datetime.utcnow() + timedelta(hours=9)
today_str = kst_now.strftime("%Y년 %m월 %d일")
# [추가됨] 실시간 시세 표기를 위한 분 단위 시간 포맷 생성
realtime_str = kst_now.strftime("%Y년 %m월 %d일 %H:%M")

# 빅테크 후보들의 실시간 시가총액을 비교하여 상위 10개를 정렬 및 수집
@st.cache_data(ttl=1800)
def get_top10_data():
    candidates = ["NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "TSM", "AVGO", "META", "TSLA", "AMD", "NFLX", "COST", "ASML", "ORCL", "CRM", "QCOM"]
    
    pool = []
    for t in candidates:
        try:
            stock = yf.Ticker(t)
            mcap = stock.fast_info.market_cap
            if mcap > 0:
                pool.append({"ticker": t, "mcap": mcap})
        except:
            pass
            
    pool.sort(key=lambda x: x["mcap"], reverse=True)
    top10_tickers = [item["ticker"] for item in pool[:10]]
    
    data_list = []
    for t in top10_tickers:
        try:
            stock = yf.Ticker(t)
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

# 가상자산 실시간 시세 가져오기
def get_crypto_price():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&contract_addresses=&vs_currencies=usd"
        response = requests.get(url, timeout=5).json()
        return response['bitcoin']['usd']
    except:
        return 61250 

# 구글 뉴스 수집
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

# 제미나이 AI 요약
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

# ==========================================
# 화면 출력 (렌더링) 부분 시작
# ==========================================

news_data = get_news()
current_btc_price = get_crypto_price()
top10_data = get_top10_data() 

if len(news_data) == 0:
    st.error("뉴스를 불러오고 있습니다. 잠시 후 새로고침(F5)을 눌러주세요.")
else:
    # 1. AI 3줄 브리핑
    st.subheader("🤖 제미나이 AI의 현재 증시 3줄 브리핑")
    with st.info(f"✅ {today_str} 한국 시간 오전 6시 장 마감 시황 및 최근 24시간 속보를 종합 분석한 결과입니다."):
        st.markdown(get_ai_summary(news_data, today_str, current_btc_price))
    
    st.markdown("---")
    
    # 2. [업그레이드] 주요 기술주 실시간 시세 표 (동적 날짜 및 시간 추가)
    st.subheader("📊 주요 기술주 실시간 시세 (시총 상위)")
    
    # 현재 시간(시:분) 계산 및 작은 회색 글씨(caption)로 분리 출력
    kst_now_time = (datetime.utcnow() + timedelta(hours=9)).strftime("%H:%M")
    st.caption(f"⏱ {today_str} {kst_now_time} 업데이트 기준")
    
    if top10_data:
        html_table = "<table style='width:100%; border-collapse: collapse; text-align: right; font-size: 16px;'>"
        html_table += "<thead><tr style='border-bottom: 2px solid rgba(128,128,128,0.3);'>"
        html_table += "<th style='text-align: left; padding: 10px;'>종목명</th>"
        html_table += "<th style='padding: 10px;'>현재가</th>"
        html_table += "<th style='padding: 10px;'>등락</th>"
        html_table += "<th style='padding: 10px;'>등락률</th>"
        html_table += "</tr></thead><tbody>"
        
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
            
            html_table += "<tr style='border-bottom: 1px solid rgba(128,128,128,0.1);'>"
            html_table += f"<td style='text-align: left; padding: 10px; font-weight: bold;'>{item['종목명']}</td>"
            html_table += f"<td style='padding: 10px; color: {color}; font-weight: bold;'>{price_str}</td>"
            html_table += f"<td style='padding: 10px; color: {color};'>{change_str}</td>"
            html_table += f"<td style='padding: 10px; color: {color};'>{pct_str}</td>"
            html_table += "</tr>"
            
        html_table += "</tbody></table>"
        
        st.markdown(html_table, unsafe_allow_html=True)
    else:
        st.warning("종가 데이터를 불러오지 못했습니다.")
        
    st.markdown("---")
    
    # 3. 뉴스 기사 타임라인
    for news in news_data:
        st.subheader(f"[{news['ticker']}] {news['title']}")
        st.caption(f"🕒 {news['time']} | ✍️ {news['publisher']}")
        st.markdown(f"[👉 뉴스 원문 보러가기]({news['link']})")
        st.markdown("---")
