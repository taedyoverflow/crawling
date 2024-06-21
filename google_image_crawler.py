from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
import urllib.request
import os
from tqdm import tqdm
import imagehash
from PIL import Image
import io

# Chrome 옵션 설정
chrome_options = Options()
chrome_options.add_argument("--headless")  # GUI 없이 headless 모드로 실행
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--log-level=3")  # 로그 레벨 설정 (콘솔 출력 최소화)

# ChromeDriver 경로
chromedriver_path = './chromedriver.exe'  # chromedriver의 상대 경로

# WebDriver 설정
service = Service(chromedriver_path)
driver = webdriver.Chrome(service=service, options=chrome_options)

def get_image_hash(image_data):
    image = Image.open(io.BytesIO(image_data))
    return imagehash.average_hash(image)

def google_image_search(query):
    search_url = f"https://www.google.com/search?hl=en&tbm=isch&q={query}"
    driver.get(search_url)
    
    # 페이지 끝까지 스크롤
    body = driver.find_element(By.TAG_NAME, "body")
    max_scroll_attempts = 50
    consecutive_scroll_failures = 0
    max_consecutive_failures = 2
    total_scroll_attempts = 0
    scroll_session_attempts = 0

    while True:
        previous_height = driver.execute_script("return document.body.scrollHeight")
        for attempt in range(max_scroll_attempts):
            body.send_keys(Keys.PAGE_DOWN)
            time.sleep(2)  # 이미지가 로드될 시간을 줌
            total_scroll_attempts += 1
            scroll_session_attempts = attempt + 1
            print(f"스크롤 시도 {scroll_session_attempts}/{max_scroll_attempts}")
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == previous_height:
            consecutive_scroll_failures += 1
            print(f"새로운 콘텐츠가 로드되지 않았습니다. 연속 실패 횟수: {consecutive_scroll_failures}/{max_consecutive_failures}")
            if consecutive_scroll_failures >= max_consecutive_failures:
                print("스크롤을 더 이상 진행할 수 없습니다. 최대 시도 횟수에 도달했습니다.")
                break
        else:
            consecutive_scroll_failures = 0
            print("새로운 콘텐츠 로드됨, 스크롤 계속 진행")

        if consecutive_scroll_failures >= max_consecutive_failures:
            break

    # 디버그: 페이지가 스크롤되었는지 확인
    print("페이지 스크롤 완료")

    # BeautifulSoup으로 페이지 소스 파싱
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    # 이미지 태그를 식별하기 위한 변경된 클래스 사용
    images = soup.find_all('img', {'src': lambda x: x and 'encrypted-tbn0.gstatic.com' in x})
    titles = [img.get('alt') for img in images]

    # 디버그: 찾은 이미지 수 출력
    print(f"찾은 이미지 수: {len(images)}")

    if not images:
        print("이미지를 찾을 수 없습니다.")
        return
    
    # 출력 디렉토리 생성
    image_dir = os.path.join(os.getcwd(), 'images')
    page_dir = os.path.join(os.getcwd(), 'titles')
    os.makedirs(image_dir, exist_ok=True)
    os.makedirs(page_dir, exist_ok=True)
    
    downloaded_images = 0
    skipped_images = 0
    image_hashes = set()
    
    for idx, (img, title) in enumerate(tqdm(zip(images, titles), total=len(images))):
        try:
            # 이미지 URL 가져오기
            img_url = img['src']
            image_data = urllib.request.urlopen(img_url).read()
            img_hash = get_image_hash(image_data)

            if img_hash in image_hashes:
                print(f"{idx + 1}번째 이미지가 중복되어 건너뜀: {img_url}")
                skipped_images += 1
                continue

            image_hashes.add(img_hash)
            image_path = os.path.join(image_dir, f'image_{img_hash}.jpg')
            title_path = os.path.join(page_dir, f'title_{img_hash}.txt')

            with open(image_path, 'wb') as img_file:
                img_file.write(image_data)

            with open(title_path, 'w', encoding='utf-8') as f:
                f.write(f"제목: {title}\n")
            
            downloaded_images += 1
            print(f"{idx + 1}번째 이미지 및 제목 저장 완료: {img_url}, {title}")

        except Exception as e:
            print(f"{idx + 1}번째 이미지 처리 중 오류 발생: {e}")
            continue

    print(f"다운로드된 유효 이미지 수: {downloaded_images}")
    print(f"중복으로 건너뛴 이미지 수: {skipped_images}")
    
    driver.quit()

if __name__ == "__main__":
    query = input("검색할 이미지를 입력하세요: ")
    google_image_search(query)
