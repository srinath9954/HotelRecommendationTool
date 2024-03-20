from flask import Flask, render_template, request
from bs4 import BeautifulSoup
import requests
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import re

app = Flask(__name__)

# Initializing the VADER sentiment analyzer
sid = SentimentIntensityAnalyzer()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/search', methods=['POST'])
def search_hotels():
    location = request.form['location']
    url = f'https://www.booking.com/searchresults.html?ss={location}%2C+India&ssne=Ooty&ssne_untouched=Ooty&efdco=1&label=gen173nr-1FCAQoggJCDWNpdHlfLTIxMTQ4ODhIM1gEaGyIAQGYATG4ARfIAQzYAQHoAQH4AQOIAgGoAgO4At--3K8GwAIB0gIkMGRhNWE1ZmItY2I2My00Y2MyLWI1YWItMjQ2ZGVhMzFhM2Rm2AIF4AIB&aid=304142&lang=en-us&sb=1&src_elem=sb&src=searchresults&dest_type=city&group_adults=1&no_rooms=1&group_children=0'

    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; CrOS x86_64 8172.45.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.64 Safari/537.36',
        'Accept-Language': 'en-US, en;q=0.5'
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        hotels = soup.findAll('div', {'data-testid': 'property-card'})

        hotels_data = []

        for hotel in hotels:
            name_element = hotel.find('div', {'data-testid': 'title'})
            name = name_element.text.strip() if name_element else None

            location_element = hotel.find('span', {'data-testid': 'address'})
            location = location_element.text.strip() if location_element else None

            rating_element = hotel.find(
                'div', {'class': 'a3b8729ab1 d86cee9b25'})
            rating_text = rating_element.text.strip() if rating_element else None

            # Extracting only the numerical part from the rating text using regular expressions
            if rating_text:
                rating_match = re.search(r'\d+\.\d+', rating_text)
                rating = float(rating_match.group()) if rating_match else None
            else:
                rating = None

            link_element = hotel.find('a', class_='a78ca197d0')
            hotel_url = link_element['href'] if link_element else None

            if location and hotel_url:
                lat, lon = get_coordinates(location)
                if lat is not None and lon is not None:
                    sentiment_score = get_sentiment_score(hotel_url)
                    hotels_data.append({
                        'name': name,
                        'location': location,
                        'rating': rating,
                        'sentiment_score': sentiment_score,
                        'lat': lat,
                        'lon': lon,
                        'link': hotel_url
                    })

        # Sort hotels based on sentiment score
        hotels_data.sort(key=lambda x: x['sentiment_score'], reverse=True)

        if hotels_data:
            return render_template('results.html', hotels=hotels_data, location=location)
        else:
            return "No hotels found for the given location"
    else:
        return "Failed to retrieve data from Booking.com"


def get_coordinates(location):
    # URL for the Nominatim API
    url = f"https://nominatim.openstreetmap.org/search?format=json&q={location}"

    # Sending a GET request to the API
    response = requests.get(url)

    # Checking if the request was successful
    if response.status_code == 200:
        # Parsing the JSON response
        data = response.json()
        if data:
            # Extracting latitude and longitude from the response
            lat = float(data[0]['lat'])
            lon = float(data[0]['lon'])
            return lat, lon
    # Return None if coordinates cannot be obtained
    return None, None


def get_sentiment_score(url):
    response_hotel = requests.get(url)
    if response_hotel.status_code == 200:
        soup_hotel = BeautifulSoup(response_hotel.content, 'html.parser')
        review_elements = soup_hotel.findAll(
            'div', {'data-testid': 'featuredreview-text'})
        reviews = [review_element.text.strip()
                   for review_element in review_elements]

        # Perform sentiment analysis
        compound_scores = [sid.polarity_scores(
            review)['compound'] for review in reviews]
        if compound_scores:
            average_score = sum(compound_scores) / len(compound_scores)
        else:
            average_score = 0.0
        return average_score
    else:
        return 0.0


if __name__ == '__main__':
    app.run(debug=True)
