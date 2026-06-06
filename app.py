import streamlit as st
import feedparser
import time

# 웹사이트 기본 설정
st.set_page_config(page_title="미국 증시 실시간 뉴스", page_icon="📈", layout="centered")

st.title("📈 미국 증시 실시간 핵심 뉴스")
st.write("주요 지수 및 기술주의 가장 빠른 영문 속보를 모아봅니다.")
st.markdown("---")

# 모니터링할 종목
tickers = ["QQQ", "SPY", "AAPL", "MSFT", "NVDA", "COIN"]

@st.cache_data(ttl=600) # 서버 과부하 방지: 10분마다 새로고침
def get_news():
    all_news = []
    
    for ticker in tickers:
        try:
            # 구글 뉴스 영문 RSS 피드 사용 (클라우드 차단 우회)
            url = f"https://news.google.com/rss/search?q={ticker}+stock+news&hl=en-US&gl=US&ceid=US:en"
            feed = feedparser.parse(url)
            
            # 각 종목당 최신 기사 5개씩만 추출
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
        except Exception as e:
            # 에러 발생 시 무시하고 다음 종목으로 넘어감
            pass
            
    # 전체 뉴스를 시간 역순(가장 최신이 위로) 정렬
    all_news.sort(key=lambda x: x["timestamp"], reverse=True)
    return all_news[:30] # 최종적으로 가장 최신 기사 30개만 보여줌

# 뉴스 데이터를 웹 화면에 출력
news_data = get_news()

# 만약 뉴스가 하나도 없다면 에러 메시지 출력
if len(news_data) == 0:
    st.error("뉴스를 불러오고 있습니다. 잠시 후 새로고침(F5)을 눌러주세요.")
else:
    for news in news_data:
        st.subheader(f"[{news['ticker']}] {news['title']}")
        st.caption(f"🕒 {news['time']} | ✍️ {news['publisher']}")
        st.markdown(f"[👉 뉴스 원문 보러가기]({news['link']})")
        st.markdown("---")
