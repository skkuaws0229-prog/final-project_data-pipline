"""
외부 Pathway API 통합 모듈

통합 API:
1. KEGG API - 경로 이미지 및 기본 정보
2. Reactome API - 생물학적 경로 상세 정보 및 시각화
3. WikiPathways API - 커뮤니티 기반 경로 데이터
"""

import urllib.request
import urllib.parse
import json
from typing import Optional


# ════════════════════════════════════════════════════════════════════════════════
#  1. KEGG API
# ════════════════════════════════════════════════════════════════════════════════
def search_kegg_pathway(pathway_name: str) -> Optional[dict]:
    """
    KEGG pathway 검색 및 정보 가져오기

    Returns:
        {
            "kegg_id": "hsa04151",
            "name": "PI3K-Akt signaling pathway - Homo sapiens",
            "image_url": "https://www.kegg.jp/pathway/hsa04151",
            "api_image_url": "http://rest.kegg.jp/get/hsa04151/image",
            "genes": [...],  # pathway에 포함된 유전자 목록
        }
    """
    try:
        # 1. KEGG pathway 검색
        search_query = urllib.parse.quote(pathway_name)
        search_url = f"http://rest.kegg.jp/find/pathway/{search_query}"

        with urllib.request.urlopen(search_url, timeout=5) as resp:
            result = resp.read().decode('utf-8').strip()

        if not result:
            return None

        # 첫 번째 결과 파싱
        first_line = result.split('\n')[0]
        parts = first_line.split('\t')
        if len(parts) < 2:
            return None

        kegg_id = parts[0].replace('path:', '')
        kegg_name = parts[1]

        # 2. Pathway 상세 정보 가져오기 (유전자 목록)
        genes = []
        try:
            genes_url = f"http://rest.kegg.jp/link/genes/{kegg_id}"
            with urllib.request.urlopen(genes_url, timeout=5) as resp:
                genes_result = resp.read().decode('utf-8').strip()
                if genes_result:
                    for line in genes_result.split('\n'):
                        parts = line.split('\t')
                        if len(parts) == 2:
                            gene_id = parts[1].split(':')[-1]  # hsa:1956 -> 1956
                            genes.append(gene_id)
        except Exception:
            pass  # 유전자 정보 없어도 계속 진행

        return {
            "kegg_id": kegg_id,
            "name": kegg_name,
            "image_url": f"https://www.kegg.jp/pathway/{kegg_id}",
            "api_image_url": f"http://rest.kegg.jp/get/{kegg_id}/image",
            "gene_count": len(genes),
            "genes": genes[:50],  # 최대 50개만
            "source": "KEGG"
        }
    except Exception as e:
        print(f"[KEGG API Error] {pathway_name}: {e}")
        return None


# ════════════════════════════════════════════════════════════════════════════════
#  2. Reactome API
# ════════════════════════════════════════════════════════════════════════════════
def search_reactome_pathway(pathway_name: str, species: str = "Homo sapiens") -> Optional[list[dict]]:
    """
    Reactome pathway 검색

    Returns:
        [
            {
                "stId": "R-HSA-109582",
                "displayName": "Hemostasis",
                "species": "Homo sapiens",
                "url": "https://reactome.org/content/detail/R-HSA-109582",
                "diagram_url": "https://reactome.org/ContentService/exporter/diagram/R-HSA-109582.png"
            },
            ...
        ]
    """
    try:
        # Reactome query API
        search_query = urllib.parse.quote(pathway_name)
        species_encoded = urllib.parse.quote(species)
        search_url = f"https://reactome.org/ContentService/search/query?query={search_query}&species={species_encoded}&types=Pathway"

        with urllib.request.urlopen(search_url, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))

        results = []
        if 'results' in data and data['results']:
            # Reactome API는 results 안에 entries 배열이 있음
            for result_group in data['results']:
                if 'entries' in result_group:
                    for item in result_group['entries'][:5]:  # 각 그룹에서 최대 5개
                        pathway_id = item.get('stId') or item.get('id')
                        # HTML 태그 제거 (<span class="highlighting">...</span>)
                        name = item.get('name', '')
                        if '<span' in name:
                            import re
                            name = re.sub(r'<[^>]+>', '', name)

                        if pathway_id and name and item.get('type') == 'Pathway':
                            species_list = item.get('species', [])
                            species_name = species_list[0] if species_list else species

                            results.append({
                                "stId": pathway_id,
                                "displayName": name,
                                "species": species_name,
                                "url": f"https://reactome.org/content/detail/{pathway_id}",
                                "diagram_url": f"https://reactome.org/ContentService/exporter/diagram/{pathway_id}.png",
                                "source": "Reactome"
                            })

                        if len(results) >= 5:  # 전체 최대 5개
                            break
                if len(results) >= 5:
                    break

        return results if results else None
    except Exception as e:
        print(f"[Reactome API Error] {pathway_name}: {e}")
        return None


def get_reactome_pathway_details(pathway_id: str) -> Optional[dict]:
    """
    Reactome pathway 상세 정보

    Args:
        pathway_id: Reactome stable ID (e.g., "R-HSA-109582")

    Returns:
        {
            "stId": "R-HSA-109582",
            "displayName": "Hemostasis",
            "summation": "...",
            "hasEvent": [...],  # 하위 이벤트
            "hasComponent": [...],  # 구성 요소
        }
    """
    try:
        url = f"https://reactome.org/ContentService/data/query/{pathway_id}"

        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))

        return {
            "stId": data.get('stId'),
            "displayName": data.get('displayName'),
            "summation": data.get('summation', [{}])[0].get('text') if data.get('summation') else None,
            "species": data.get('species', [{}])[0].get('displayName') if data.get('species') else None,
            "hasEvent": [e.get('displayName') for e in data.get('hasEvent', [])[:10]],
            "url": f"https://reactome.org/content/detail/{pathway_id}",
            "diagram_url": f"https://reactome.org/ContentService/exporter/diagram/{pathway_id}.png",
            "source": "Reactome"
        }
    except Exception as e:
        print(f"[Reactome API Error] {pathway_id}: {e}")
        return None


# ════════════════════════════════════════════════════════════════════════════════
#  3. WikiPathways API
# ════════════════════════════════════════════════════════════════════════════════
def search_wikipathways(pathway_name: str, species: str = "Homo sapiens") -> Optional[list[dict]]:
    """
    WikiPathways 검색 (API 제한으로 인해 직접 검색 링크 반환)

    Returns:
        [
            {
                "search_url": "https://www.wikipathways.org/search?query=...",
                "message": "WikiPathways에서 직접 검색하세요"
            }
        ]
    """
    # WikiPathways API가 현재 제한적이므로 검색 URL만 제공
    search_query = urllib.parse.quote(pathway_name)

    return [{
        "search_url": f"https://www.wikipathways.org/search?query={search_query}",
        "message": f"WikiPathways에서 '{pathway_name}' 검색",
        "note": "WikiPathways API 접근 제한으로 직접 링크 제공",
        "source": "WikiPathways"
    }]


def get_wikipathways_details(pathway_id: str) -> Optional[dict]:
    """
    WikiPathways pathway 상세 정보

    Args:
        pathway_id: WikiPathways ID (e.g., "WP254")

    Returns:
        {
            "id": "WP254",
            "name": "Apoptosis",
            "organism": "Homo sapiens",
            "description": "...",
            "genes": [...],
            "url": "https://www.wikipathways.org/pathways/WP254"
        }
    """
    try:
        url = f"https://webservice.wikipathways.org/getPathwayInfo?pwId={pathway_id}&format=json"

        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))

        pathway = data.get('pathwayInfo', {})

        return {
            "id": pathway.get('id'),
            "name": pathway.get('name'),
            "organism": pathway.get('species'),
            "url": pathway.get('url'),
            "revision": pathway.get('revision'),
            "description": pathway.get('description'),
            "png_url": f"https://www.wikipathways.org/wpi/wpi.php?action=downloadFile&type=png&pwTitle=Pathway:{pathway_id}",
            "source": "WikiPathways"
        }
    except Exception as e:
        print(f"[WikiPathways API Error] {pathway_id}: {e}")
        return None


# ════════════════════════════════════════════════════════════════════════════════
#  통합 검색 함수
# ════════════════════════════════════════════════════════════════════════════════
def search_all_pathways(pathway_name: str) -> dict:
    """
    세 가지 API에서 모두 검색

    Returns:
        {
            "kegg": {...},
            "reactome": [{...}, ...],
            "wikipathways": [{...}, ...]
        }
    """
    results = {
        "kegg": None,
        "reactome": None,
        "wikipathways": None
    }

    # 병렬로 검색하면 더 빠르지만, 순차적으로 해도 충분히 빠름
    results["kegg"] = search_kegg_pathway(pathway_name)
    results["reactome"] = search_reactome_pathway(pathway_name)
    results["wikipathways"] = search_wikipathways(pathway_name)

    return results


# ════════════════════════════════════════════════════════════════════════════════
#  테스트
# ════════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    # 테스트 1: PI3K-Akt pathway
    print("=" * 60)
    print("  PI3K-Akt pathway 검색")
    print("=" * 60)

    results = search_all_pathways("PI3K-Akt signaling")

    print("\n[KEGG]")
    if results["kegg"]:
        kegg = results["kegg"]
        print(f"  ID: {kegg['kegg_id']}")
        print(f"  Name: {kegg['name']}")
        print(f"  Genes: {kegg['gene_count']}개")
        print(f"  URL: {kegg['image_url']}")
    else:
        print("  결과 없음")

    print("\n[Reactome]")
    if results["reactome"]:
        for r in results["reactome"]:
            print(f"  ID: {r['stId']}")
            print(f"  Name: {r['displayName']}")
            print(f"  URL: {r['url']}")
            print()
    else:
        print("  결과 없음")

    print("\n[WikiPathways]")
    if results["wikipathways"]:
        for w in results["wikipathways"]:
            if 'search_url' in w:
                print(f"  검색 URL: {w['search_url']}")
                print(f"  메시지: {w['message']}")
            else:
                print(f"  ID: {w.get('id', 'N/A')}")
                print(f"  Name: {w.get('name', 'N/A')}")
                print(f"  URL: {w.get('url', 'N/A')}")
            print()
    else:
        print("  결과 없음")

    # 테스트 2: Apoptosis
    print("\n" + "=" * 60)
    print("  Apoptosis 검색")
    print("=" * 60)

    results = search_all_pathways("Apoptosis")
    print(f"\nKEGG: {1 if results['kegg'] else 0}개")
    print(f"Reactome: {len(results['reactome']) if results['reactome'] else 0}개")
    print(f"WikiPathways: {len(results['wikipathways']) if results['wikipathways'] else 0}개")
