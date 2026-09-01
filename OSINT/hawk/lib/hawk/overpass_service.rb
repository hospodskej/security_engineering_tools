require 'httparty'

module Hawk
  class OverpassService
    include HTTParty
    base_uri 'https://overpass-api.de/api'

    def self.nearby(lat, lon, radius = 1000, limit = 50)
      query = <<~QL
        [out:json][timeout:25];
        (
          node(around:#{radius},#{lat},#{lon})["amenity"];
          way(around:#{radius},#{lat},#{lon})["amenity"];
          relation(around:#{radius},#{lat},#{lon})["amenity"];
          node(around:#{radius},#{lat},#{lon})["shop"];
          way(around:#{radius},#{lat},#{lon})["shop"];
          node(around:#{radius},#{lat},#{lon})["tourism"];
          way(around:#{radius},#{lat},#{lon})["tourism"];
          node(around:#{radius},#{lat},#{lon})["building"];
          way(around:#{radius},#{lat},#{lon})["building"];
          node(around:#{radius},#{lat},#{lon})["public_transport"];
          way(around:#{radius},#{lat},#{lon})["public_transport"];
          node(around:#{radius},#{lat},#{lon})["highway"="bus_stop"];
          node(around:#{radius},#{lat},#{lon})["railway"="station"];
          node(around:#{radius},#{lat},#{lon})["aeroway"];
        );
        out center tags #{limit};
      QL

      max_retries = 3
      retries = 0
      begin
        response = post('/interpreter', body: { data: query })
        raise "Overpass API error: #{response.code}" unless response.success?
      rescue => e
        retries += 1
        if retries < max_retries
          sleep 2 * retries
          retry
        else
          raise e
        end
      end

      data = JSON.parse(response.body)
      elements = data['elements'] || []

      facilities = elements.filter_map do |el|
        if el['lat'] && el['lon']
          facility_lat = el['lat']
          facility_lon = el['lon']
        elsif el['center']
          facility_lat = el['center']['lat']
          facility_lon = el['center']['lon']
        else
          next
        end

        tags = el['tags'] || {}
        category = %w[amenity shop tourism building public_transport highway railway aeroway].find { |k| tags.key?(k) }
        name = tags['name'] || tags['brand'] || "#{category} (unnamed)"

        distance = haversine(lat, lon, facility_lat, facility_lon)

        {
          name: name,
          category: category,
          type: el['type'],
          lat: facility_lat,
          lon: facility_lon,
          tags: tags,
          distance: distance
        }
      end

      deduped = {}
      facilities.each do |f|
        key = f[:name].downcase
        if !deduped.key?(key) || f[:distance] < deduped[key][:distance]
          deduped[key] = f
        end
      end

      deduped.values.sort_by { |f| f[:distance] }.first(limit)
    end

    private

    def self.haversine(lat1, lon1, lat2, lon2)
      earth_radius = 6371000 # meters
      dlat = (lat2 - lat1) * Math::PI / 180
      dlon = (lon2 - lon1) * Math::PI / 180
      a = Math.sin(dlat/2)**2 + Math.cos(lat1 * Math::PI / 180) * Math.cos(lat2 * Math::PI / 180) * Math.sin(dlon/2)**2
      c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a))
      earth_radius * c
    end
  end
end