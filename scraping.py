import os
import csv
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

visited_urls = set()  # 訪問済みのURLを保存するセット
robots_cache = {}  # robots.txtをキャッシュして再利用

def fetch_robots_txt(url: str) -> str:
    """
    指定されたURLのドメインのrobots.txtを取得します。
    
    Args:
    - url (str): チェックしたいページのURL
    
    Returns:
    - str: robots.txtの内容
    """
    parsed_url = urlparse(url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    
    if base_url in robots_cache:
        return robots_cache[base_url]  # キャッシュがあれば再利用

    robots_url = f"{base_url}/robots.txt"
    
    try:
        response = requests.get(robots_url)
        response.raise_for_status()
        robots_txt = response.text
        robots_cache[base_url] = robots_txt  # キャッシュに保存
        return robots_txt

    except requests.exceptions.RequestException as e:
        print(f"robots.txtの取得中にエラーが発生しました: {e}")
        return ""


def is_allowed_by_robots(url: str, robots_txt: str) -> bool:
    """
    URLがrobots.txtで許可されているかをチェックします。
    
    Args:
    - url (str): チェックしたいURL
    - robots_txt (str): robots.txtの内容
    
    Returns:
    - bool: 許可されていればTrue、禁止されていればFalse
    """
    parsed_url = urlparse(url)
    path = parsed_url.path

    # robots.txtを行ごとに解析
    user_agent_allowed = False
    disallowed_paths = []
    allowed_paths = []

    for line in robots_txt.splitlines():
        line = line.strip()
        if line.startswith("User-agent: *"):
            user_agent_allowed = True
        elif line.startswith("Disallow:") and user_agent_allowed:
            disallowed_path = line.split(":")[1].strip()
            disallowed_paths.append(disallowed_path)
        elif line.startswith("Allow:") and user_agent_allowed:
            allowed_path = line.split(":")[1].strip()
            allowed_paths.append(allowed_path)

    # Allowに一致する場合は許可
    for allowed in allowed_paths:
        if path.startswith(allowed):
            return True

    # Disallowに一致する場合は許可しない
    for disallowed in disallowed_paths:
        if path.startswith(disallowed):
            return False

    return True  # 特に指定がない場合は許可


def scrape_links(url: str) -> list:
    """
    指定されたURLからすべてのリンクを取得し、返します。
    
    Args:
    - url (str): スクレイピングするページのURL
    
    Returns:
    - list: ページ内のリンクURLのリスト
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        # ページ内のすべてのリンクを取得
        links = []
        for link in soup.find_all("a", href=True):
            full_url = urljoin(url, link["href"])  # 相対URLを絶対URLに変換
            if urlparse(full_url).netloc == urlparse(url).netloc:
                links.append(full_url)

        return links
    
    except requests.exceptions.RequestException as e:
        print(f"リンクの取得中にエラーが発生しました: {e}")
        return []


def save_urls_to_csv(url_depth_list: list, output_csv: str) -> None:
    """
    取得したURLリストをCSVファイルに保存します。
    
    Args:
    - url_depth_list (list): 保存するURLと深さのタプルのリスト
    - output_csv (str): 保存するCSVファイルのパス
    """
    with open(output_csv, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["URL", "Depth"])  # CSVのヘッダー行
        for url, depth in url_depth_list:
            writer.writerow([url, depth])
    
    print(f"{len(url_depth_list)}個のURLが {output_csv} に保存されました。")


def crawl_site(url: str, depth: int, current_depth: int = 0, url_depth_list: list = []) -> None:
    """
    指定されたURLから再帰的にリンクをたどり、すべてのURLを収集します。
    
    Args:
    - url (str): 開始するページのURL
    - depth (int): 再帰的にたどる深さ（0の場合はリンクをたどらない）
    - current_depth (int): 現在の深さ
    - url_depth_list (list): URLと深さを保存するリスト
    """
    if url in visited_urls:
        return
    if current_depth > depth:
        return
    
    print(f"現在のURL: {url}, 深さ: {current_depth}")
    
    # 訪問済みURLに追加
    visited_urls.add(url)

    # URLと深さをリストに追加
    url_depth_list.append((url, current_depth))

    # robots.txtを確認
    robots_txt = fetch_robots_txt(url)
    if robots_txt and not is_allowed_by_robots(url, robots_txt):
        print(f"robots.txtにより {url} はスクレイピングが許可されていません。")
        return
    
    # 現在のページのリンクを取得
    links = scrape_links(url)

    # 再帰的にリンクをたどる
    for link in links:
        if link not in visited_urls:
            crawl_site(link, depth, current_depth + 1, url_depth_list)


def main():
    target_url = "https://www.nta.go.jp/users/gensen/nencho/index.htm"
    output_csv = "scraped_urls_with_depth.csv"
    crawl_depth = 2  # 再帰的にたどる深さを設定

    # URLと深さを保存するリスト
    url_depth_list = []

    # 再帰的にスクレイピングを開始
    crawl_site(target_url, crawl_depth, current_depth=0, url_depth_list=url_depth_list)
    
    # 取得したすべてのURLと深さをCSVに保存
    save_urls_to_csv(url_depth_list, output_csv)


if __name__ == "__main__":
    main()
