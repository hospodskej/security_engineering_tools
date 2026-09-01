module Hawk
  class Profiler
    def self.profile(input, radius: 1000, facility_limit: 50)
      if input.is_a?(String)
        location = GeocoderService.geocode(input)
        raise "Could not geocode address: #{input}" unless location
        lat = location[:lat]
        lon = location[:lon]
      elsif input.is_a?(Array) && input.size == 2
        lat, lon = input
        location = GeocoderService.reverse_geocode(lat, lon)
        location ||= { lat: lat, lon: lon, display_name: "Coordinates #{lat}, #{lon}", address: {} }
      else
        raise ArgumentError, "Input must be an address string or [lat, lon] array"
      end

      facilities = OverpassService.nearby(lat, lon, radius, facility_limit)
      elevation = ElevationService.get_elevation(lat, lon)
      weather = WeatherService.current_weather(lat, lon)

      {
        location: location,
        coordinates: { lat: lat, lon: lon },
        radius: radius,
        facilities: facilities,
        elevation: elevation,
        weather: weather,
        generated_at: Time.now.utc
      }
    end
  end
end