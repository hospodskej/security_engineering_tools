require 'httparty'
require 'json'

module Hawk
  class GeocoderService
    include HTTParty
    base_uri 'https://nominatim.openstreetmap.org'

    headers 'User-Agent' => "Hawk/#{VERSION} (pavelpatockaa@gmail.com)"

    def self.geocode(address)
      response = get('/search', query: {
        q: address,
        format: 'json',
        limit: 1,
        addressdetails: 1
      })

      if response.success?
        data = JSON.parse(response.body)
        return nil if data.empty?

        item = data.first
        {
          lat: item['lat'].to_f,
          lon: item['lon'].to_f,
          display_name: item['display_name'],
          address: item['address'] || {}
        }
      else
        raise "Nominatim geocoding failed: #{response.code} - #{response.body}"
      end
    end

    def self.reverse_geocode(lat, lon)
      response = get('/reverse', query: {
        lat: lat,
        lon: lon,
        format: 'json',
        addressdetails: 1
      })

      if response.success?
        data = JSON.parse(response.body)
        return nil if data.empty?

        {
          lat: data['lat'].to_f,
          lon: data['lon'].to_f,
          display_name: data['display_name'],
          address: data['address'] || {}
        }
      else
        raise "Nominatim reverse geocoding failed: #{response.code} - #{response.body}"
      end
    end
  end
end