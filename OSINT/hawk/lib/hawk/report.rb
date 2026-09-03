require 'rainbow'

module Hawk
  class Report
    WMO_CODES = {
      0 => "Clear sky",
      1 => "Mainly clear",
      2 => "Partly cloudy",
      3 => "Overcast",
      45 => "Fog",
      48 => "Depositing rime fog",
      51 => "Light drizzle",
      53 => "Moderate drizzle",
      55 => "Dense drizzle",
      56 => "Light freezing drizzle",
      57 => "Dense freezing drizzle",
      61 => "Slight rain",
      63 => "Moderate rain",
      65 => "Heavy rain",
      66 => "Light freezing rain",
      67 => "Heavy freezing rain",
      71 => "Slight snowfall",
      73 => "Moderate snowfall",
      75 => "Heavy snowfall",
      77 => "Snow grains",
      80 => "Slight rain showers",
      81 => "Moderate rain showers",
      82 => "Violent rain showers",
      85 => "Slight snow showers",
      86 => "Heavy snow showers",
      95 => "Thunderstorm",
      96 => "Thunderstorm with slight hail",
      99 => "Thunderstorm with heavy hail"
    }.freeze

    def self.generate(profile, format: :text, color: true)
      case format
      when :json
        JSON.pretty_generate(profile)
      else
        text_report(profile, color)
      end
    end

    private

    def self.weather_description(code)
      WMO_CODES[code.to_i] || "Unknown weather (code #{code})"
    end

    def self.text_report(profile, color)
      lines = []
      loc = profile[:location]
      coord = profile[:coordinates]

      lines << "HAWK - OSINT Geographical Recon & Facility Profiler"
      lines << "=" * 60
      lines << "Location: #{loc[:display_name]}"
      lines << "Coordinates: #{coord[:lat]}, #{coord[:lon]}"
      lines << "Generated at: #{profile[:generated_at]}"
      lines << "Search radius: #{profile[:radius]} meters"
      lines << ""

      lines << "Elevation: #{profile[:elevation] ? "#{profile[:elevation].round(2)} m" : 'N/A'}"
      lines << ""

      weather = profile[:weather]
      if weather && weather['temperature']
        lines << "Current Weather:"
        lines << "  Temperature: #{weather['temperature']}°C"
        lines << "  Wind Speed: #{weather['windspeed']} km/h"
        lines << "  Conditions: #{weather_description(weather['weathercode'])}"
        lines << ""
      end

      facilities = profile[:facilities]
      if facilities.empty?
        lines << "No facilities found within radius."
      else
        lines << "Nearby Facilities (#{facilities.size} found):"
        facilities.each do |f|
          cat = f[:category].to_s.capitalize
          name = f[:name]
          dist = f[:distance].round(0)
          lines << "  - [#{cat}] #{name} (#{dist}m)"
        end
      end

      text = lines.join("\n")

      if color
        text = text.gsub(/^HAWK - OSINT Geographical.*$/, Rainbow($&).cyan.bright)
        text = text.gsub(/^Location:.*$/, Rainbow($&).green)
        text = text.gsub(/^Elevation:.*$/, Rainbow($&).yellow)
        text = text.gsub(/^Current Weather:.*$/, Rainbow($&).yellow)
        text = text.gsub(/^Nearby Facilities.*$/, Rainbow($&).magenta)
        text = text.gsub(/^  - .*$/) { |line| Rainbow(line).blue }
      end

      text
    end
  end
end