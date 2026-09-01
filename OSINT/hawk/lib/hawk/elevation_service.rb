require 'httparty'

module Hawk
  class ElevationService
    include HTTParty
    base_uri 'https://api.open-elevation.com/api/v1'

    def self.get_elevation(lat, lon)
      response = get('/lookup', query: { locations: "#{lat},#{lon}" })
      raise "Open-Elevation API error: #{response.code}" unless response.success?

      data = JSON.parse(response.body)
      result = data['results']&.first
      result ? result['elevation'].to_f : nil
    end
  end
end