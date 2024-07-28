from flask import Flask, render_template, request
from bs4 import BeautifulSoup
import requests
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import re
import nltk
import time

# Download the VADER lexicon for sentiment analysis
nltk.download('vader_lexicon')

app = Flask(__name__)
sid = SentimentIntensityAnalyzer()

def get_response(url, headers, retries=3):
    while retries > 0:
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response
            else:
                print(f"Failed to retrieve data, status code: {response.status_code}")
                retries -= 1
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            retries -= 1
        time.sleep(2)
    return None

def get_sentiment_score(url):
    response_hotel = requests.get(url)
    if response_hotel.status_code == 200:
        soup_hotel = BeautifulSoup(response_hotel.content, 'html.parser')
        review_elements = soup_hotel.findAll('div', {'data-testid': 'featuredreview-text'})  # Update class as needed
        reviews = [review_element.get_text(strip=True) for review_element in review_elements]

        compound_scores = [sid.polarity_scores(review)['compound'] for review in reviews]
        if compound_scores:
            average_score = sum(compound_scores) / len(compound_scores)
        else:
            average_score = 0.0
        return average_score
    else:
        return 0.0

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search_hotels():
    base_url = 'https://www.booking.com'
    location = request.form['location']
    location_encoded = requests.utils.quote(location)
    url = f'https://www.booking.com/searchresults.html?ss={location_encoded}%2C+India&ssne=Ooty&ssne_untouched=Ooty&efdco=1&label=gen173nr-1FCAQoggJCDWNpdHlfLTIxMTQ4ODhIM1gEaGyIAQGYATG4ARfIAQzYAQHoAQH4AQOIAgGoAgO4At--3K8GwAIB0gIkMGRhNWE1ZmItY2I2My00Y2MyLWI1YWItMjQ2ZGVhMzFhM2Rm2AIF4AIB&aid=304142&lang=en-us&sb=1&src_elem=sb&src=searchresults&dest_type=city&group_adults=1&no_rooms=1&group_children=0'

    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; CrOS x86_64 8172.45.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.64 Safari/537.36',
        'Accept-Language': 'en-US, en;q=0.5'
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

        

        hotels = soup.findAll('div', {'data-testid': 'property-card'})  # Update class as needed
        hotels_data = []

        for hotel in hotels:
            try:
                name_element = hotel.find('div', {'data-testid': 'title'})  # Update class as needed
                name = name_element.text.strip() if name_element else 'No Name'

                location_element = hotel.find('span', {'data-testid': 'address'})
                location = location_element.text.strip() if location_element else None

                rating_element = hotel.find('div', {'data-testid': 'review-score'})  # Update class as needed
                if rating_element:
                    rating_text = rating_element.get_text(strip=True)
                    rating_match = re.search(r'\d+\.\d+', rating_text)
                    rating = rating_match.group() if rating_match else None
                else:
                    rating = None

                link_element = hotel.find('a', class_='f0ebe87f68')  # Update class as needed
                if link_element:
                    relative_url = link_element['href']
                    hotel_url = requests.compat.urljoin(base_url, relative_url)

                    sentiment_score = get_sentiment_score(hotel_url)

                    hotels_data.append({
                        'name': name,
                        'location': location,
                        'rating': rating,
                        'sentiment_score': sentiment_score
                    })

            except Exception as e:
                print(f"Error processing hotel data: {e}")

        hotels_data.sort(key=lambda x: x['sentiment_score'], reverse=True)

        if hotels_data:
            return render_template('results.html', hotels=hotels_data, location=location)
        else:
            return "No hotels found for the given location"
    else:
        return f"Failed to retrieve data from Booking.com, Status Code: {response.status_code}"

if __name__ == '__main__':
    app.run(debug=False,host='0.0.0.0')
