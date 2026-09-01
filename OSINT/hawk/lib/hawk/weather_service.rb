require 'httparty'

module Hawk
  class WeatherService
    include HTTParty
    base_uri 'https://api.open-meteo.com/v1'

    def self.current_weather(lat, lon)
      response = get('/forecast', query: {
        latitude: lat,
        longitude: lon,
        current_weather: true
      })
      raise "Open-Meteo API error: #{response.code}" unless response.success?

      data = JSON.parse(response.body)
      data['current_weather'] || {}
    end
  end
end