"""
天氣服務層
處理天氣資料獲取與快取 - 使用台灣中央氣象署 API
"""
import requests
from datetime import datetime, timedelta
from typing import Optional
from database.models import WeatherData

class WeatherService:
    def __init__(self, api_key: str, cache_hours: int = 1):
        self.api_key = api_key
        self.cache_hours = cache_hours
        self._cache = {}  # {city: (weather_data, timestamp)}
    
    def get_weather(self, city: str) -> Optional[WeatherData]:
        """
        獲取天氣資料(含快取機制) - 使用中央氣象署 API
        
        Args:
            city: 城市名稱 (例如: 臺北市, 高雄市)
            
        Returns:
            WeatherData 或 None
        """
        # 檢查快取
        if city in self._cache:
            cached_data, cached_time = self._cache[city]
            if datetime.now() - cached_time < timedelta(hours=self.cache_hours):
                return cached_data
        
        # 獲取新資料
        try:
            # 中央氣象署開放資料平台 API
            url = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0001-001"
            params = {
                "Authorization": self.api_key,
                "StationName": city.replace("市", "").replace("縣", "")  # 移除「市」或「縣」字
            }
            
            # 使用 verify=False 繞過 SSL 驗證 (解決 Render 上 Missing Subject Key Identifier 錯誤)
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            response = requests.get(url, params=params, timeout=10, verify=False)
            
            response.raise_for_status()
            data = response.json()
            
            # 檢查回應格式
            if not data.get('success'):
                print(f"天氣 API 回應異常: {data}")
                return None
            
            # 解析資料 - 使用正確的結構
            records = data.get('records', {})
            stations = records.get('Station', [])
            
            if not stations:
                print(f"找不到城市 {city} 的氣象站資料")
                return None
            
            # 取第一個氣象站的資料
            station = stations[0]
            weather_element = station.get('WeatherElement', {})
            
            # 提取溫度和天氣描述
            temp = float(weather_element.get('AirTemperature', 0))
            humidity = float(weather_element.get('RelativeHumidity', 0))
            weather_desc = weather_element.get('Weather', '晴')
            
            # 計算體感溫度 (簡化版熱指數公式)
            # 當溫度高於26度且濕度高時,體感溫度會上升
            if temp > 26 and humidity > 60:
                feels_like = temp + ((humidity - 60) / 100) * 3
            elif temp < 10:  # 低溫時考慮風寒效應
                feels_like = temp - 2
            else:
                feels_like = temp
            
            weather_data = WeatherData(
                temp=temp,
                feels_like=round(feels_like, 1),
                desc=weather_desc,
                city=city,
                update_time=datetime.now()
            )
            
            # 更新快取
            self._cache[city] = (weather_data, datetime.now())
            
            return weather_data
            
        except requests.exceptions.Timeout:
            print(f"天氣 API 請求超時: {city}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"天氣 API 請求失敗: {str(e)}")
            return None
        except (KeyError, ValueError, IndexError) as e:
            print(f"天氣資料解析失敗: {str(e)}")
            return None
        except Exception as e:
            print(f"天氣資料處理失敗: {str(e)}")
            return None
    
    def clear_cache(self):
        """清除快取"""
        self._cache.clear()
