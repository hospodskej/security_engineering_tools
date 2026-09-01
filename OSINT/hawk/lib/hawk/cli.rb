require 'thor'
require 'rainbow'

module Hawk
  class CLI < Thor
    desc "profile LOCATION", "Generate a full OSINT profile for an address or 'lat,lon'"
    method_option :radius, type: :numeric, default: 1000, aliases: '-r', desc: "Search radius in meters"
    method_option :limit, type: :numeric, default: 50, aliases: '-l', desc: "Maximum number of facilities to return"
    method_option :format, type: :string, default: 'text', enum: ['text', 'json'], aliases: '-f', desc: "Output format"
    method_option :no_color, type: :boolean, default: false, desc: "Disable colored output"
    def profile(location)
      begin
        if location =~ /^\s*([-+]?\d+\.?\d*)\s*,\s*([-+]?\d+\.?\d*)\s*$/
          lat = $1.to_f
          lon = $2.to_f
          input = [lat, lon]
        else
          input = location
        end

        say "Running HAWK profiling for #{location}..."
        result = Profiler.profile(input, radius: options[:radius], facility_limit: options[:limit])

        if options[:format] == 'json'
          puts Report.generate(result, format: :json)
        else
          puts Report.generate(result, format: :text, color: !options[:no_color])
        end
      rescue => e
        say Rainbow("Error: #{e.message}").red
        exit 1
      end
    end

    desc "geocode ADDRESS", "Geocode an address and show coordinates"
    def geocode(address)
      loc = GeocoderService.geocode(address)
      if loc
        puts "Latitude: #{loc[:lat]}"
        puts "Longitude: #{loc[:lon]}"
        puts "Display Name: #{loc[:display_name]}"
      else
        puts Rainbow("Could not geocode address.").red
      end
    end

    desc "reverse LAT LON", "Reverse geocode coordinates and show address"
    def reverse(lat, lon)
      loc = GeocoderService.reverse_geocode(lat.to_f, lon.to_f)
      if loc
        puts "Display Name: #{loc[:display_name]}"
        puts "Latitude: #{loc[:lat]}"
        puts "Longitude: #{loc[:lon]}"
      else
        puts Rainbow("Could not reverse geocode coordinates.").red
      end
    end

    desc "facilities LOCATION", "List nearby facilities only"
    method_option :radius, type: :numeric, default: 1000, aliases: '-r'
    method_option :limit, type: :numeric, default: 50, aliases: '-l'
    def facilities(location)
      if location =~ /^\s*([-+]?\d+\.?\d*)\s*,\s*([-+]?\d+\.?\d*)\s*$/
        lat, lon = $1.to_f, $2.to_f
      else
        loc = GeocoderService.geocode(location)
        raise "Could not geocode address" unless loc
        lat, lon = loc[:lat], loc[:lon]
      end

      facilities = OverpassService.nearby(lat, lon, options[:radius], options[:limit])
      facilities.each do |f|
        puts "[#{f[:category]}] #{f[:name]} - #{f[:distance].round(0)}m"
      end
    end

    desc "weather LOCATION", "Show current weather for a location"
    def weather(location)
      if location =~ /^\s*([-+]?\d+\.?\d*)\s*,\s*([-+]?\d+\.?\d*)\s*$/
        lat, lon = $1.to_f, $2.to_f
      else
        loc = GeocoderService.geocode(location)
        raise "Could not geocode address" unless loc
        lat, lon = loc[:lat], loc[:lon]
      end

      weather = WeatherService.current_weather(lat, lon)
      puts "Temperature: #{weather['temperature']}°C"
      puts "Wind Speed: #{weather['windspeed']} km/h"
      puts "Weather Code: #{weather['weathercode']}"
    end

    desc "elevation LOCATION", "Show elevation for a location"
    def elevation(location)
      if location =~ /^\s*([-+]?\d+\.?\d*)\s*,\s*([-+]?\d+\.?\d*)\s*$/
        lat, lon = $1.to_f, $2.to_f
      else
        loc = GeocoderService.geocode(location)
        raise "Could not geocode address" unless loc
        lat, lon = loc[:lat], loc[:lon]
      end

      elev = ElevationService.get_elevation(lat, lon)
      puts "Elevation: #{elev ? "#{elev.round(2)} m" : 'N/A'}"
    end

    desc "version", "Show version"
    def version
      puts "HAWK v#{VERSION}"
    end
  end
end