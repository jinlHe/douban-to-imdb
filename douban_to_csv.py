import os
import sys
import csv
import requests
from datetime import datetime
from bs4 import BeautifulSoup

USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_2) AppleWebKit/537.36 (KHTML, like Gecko) ' \
             'Chrome/47.0.2526.106 Safari/537.36 '
START_DATE = '20050502'
IS_OVER = False

# Replace with your Douban cookies
DOUBAN_COOKIES = {
    "bid": "4Y7tnIR7S3I",
    "dbcl2": "172989509:Ktl1GWAiTfU",
    "ck": "xtDP",
    # Add more cookies as needed
}

session = requests.Session()
session.headers.update({
    'User-Agent': USER_AGENT
})
session.cookies.update(DOUBAN_COOKIES)

def get_rating(rating_class):
    """
    :param rating_class: string
    :return: int
    example: "rating1-t" => 1
                "rating2-t" => 2
    """
    return int(rating_class[6])


def get_imdb_id(url):
    r = session.get(url, headers={'User-Agent': USER_AGENT})
    soup = BeautifulSoup(r.text, 'lxml')
    info_area = soup.find(id='info')
    imdb_id = None
    try:
        if info_area:
            # 由于豆瓣页面更改，IMDB的ID处不再有链接更改查询方法
            for index in range(-1, -len(info_area.find_all('span')) + 1, -1):
                imdb_id = info_area.find_all('span')[index].next_sibling.strip()
                if imdb_id.startswith('tt'):
                    break
        else:
            print('请手动添加', url)
    except:
        print('无法获得IMDB编号的电影页面：', url)
    finally:
        return imdb_id if not imdb_id or imdb_id.startswith('tt') else None


def read_existing_csv():
    file_name = os.path.dirname(os.path.abspath(__file__)) + '/movie.csv'
    existing_links = set()
    if os.path.exists(file_name):
        with open(file_name, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 4:  # 确保行有足够的列
                    existing_links.add(row[3])  # douban_link在第4列
    return existing_links


def get_info(url, existing_links):
    info = []
    r = session.get(url, headers={'User-Agent': USER_AGENT})
    soup = BeautifulSoup(r.text, "lxml")
    movie_items = soup.find_all("div", {"class": "item"})
    if len(movie_items) > 0:
        for item in movie_items:
            # meta data
            douban_link = item.a['href']
            
            # 如果链接已存在，跳过
            if douban_link in existing_links:
                print(f'跳过已存在的电影: {douban_link}')
                continue
                
            title = item.find("li", {"class": "title"}).em.text

            rating = item.find(
                "span", {"class": "date"}).find_previous_siblings()
            if len(rating) > 0:
                rating = get_rating(rating[0]['class'][0])
            else:
                rating = None

            comment = item.find("span", {"class": "comment"})
            if comment is not None:
                comment = comment.contents[0].strip()

            comment_date = item.find("span", {"class": "date"})
            if comment_date is not None:
                comment_date = comment_date.contents[0].strip()

            imdb = get_imdb_id(douban_link)

            if datetime.strptime(comment_date, '%Y-%m-%d') <= datetime.strptime(START_DATE, '%Y%m%d'):
                global IS_OVER
                IS_OVER = True
                break

            info.append([title, rating, imdb, douban_link])
    else:
        return []

    return info


def get_max_index(user_id):
    url = f"https://movie.douban.com/people/{user_id}/collect"
    r = session.get(url, headers={'User-Agent': USER_AGENT})
    soup = BeautifulSoup(r.text, "lxml")

    paginator = soup.find("div", {"class": "paginator"})
    if paginator is not None:
        max_index = paginator.find_all("a")[-2].get_text()
    else:
        max_index = 1
    print(f'总共 {max_index} 页')
    return int(max_index)


def url_generator(user_id):
    max_index = get_max_index(user_id)
    for index in range(0, max_index * 15, 15):
        yield f"https://movie.douban.com/people/{user_id}/collect" \
              f"?start={index}&sort=time&rating=all&filter=all&mode=grid"


def export(user_id):
    # 读取已存在的链接
    existing_links = read_existing_csv()
    
    urls = url_generator(user_id)
    info = []
    page_no = 1
    for url in urls:
        if IS_OVER:
            break
        print(f'开始处理第 {page_no} 页...')
        info.extend(get_info(url, existing_links))
        page_no += 1
    print(f'处理完成, 总共处理了 {len(info)} 部电影')
    
    file_name = os.path.dirname(os.path.abspath(__file__)) + '/movie.csv'
    
    # 如果文件已存在，追加写入；否则创建新文件
    mode = 'a' if os.path.exists(file_name) else 'w'
    with open(file_name, mode, encoding='utf-8', newline='') as f:
        writer = csv.writer(f, lineterminator='\n')
        writer.writerows(info)
    print('保存电影评分至：', file_name)


def check_user_exist(user_id):
    r = session.get(f'https://movie.douban.com/people/{user_id}/', headers={'User-Agent': USER_AGENT})
    soup = BeautifulSoup(r.text, 'lxml')
    if '页面不存在' in soup.title:
        return False
    else:
        return True


if __name__ == '__main__':
    # if len(sys.argv) == 1:
    #     print('请输入豆瓣ID，关于如何运行此程序请参照：',
    #           'https://github.com/fisheepx/douban-to-imdb')
    #     sys.exit()
    # if not check_user_exist(sys.argv[1]):
    #     print('请输入正确的豆瓣ID，如何查找自己的豆瓣ID 请参照：',
    #           'https://github.com/fisheepx/douban-to-imdb')
    #     sys.exit()
    # if len(sys.argv) == 3:
    #     START_DATE = sys.argv[2]
    print(f'开始抓取{START_DATE + "之后的" if START_DATE != "20050502" else "所有"}观影数据...')
    export(172989509)
