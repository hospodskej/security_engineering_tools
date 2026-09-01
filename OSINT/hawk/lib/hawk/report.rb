require 'rainbow'

module Hawk
  class Report
    def self.generate(profile, format: :text, color: true)
      case format
      when :json
        JSON.pretty_generate(profile)
      else
        text_report(profile, color)
      end
    end

    private

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
        lines << "  Conditions Code: #{weather['weathercode']}"
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