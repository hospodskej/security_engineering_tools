#!/usr/bin/env ruby

require 'thor'
require 'exifr'
require 'exifr/jpeg'
require 'exifr/tiff'
require 'json'
require 'fileutils'
require 'colorize'
require 'erb'


class ExifMap < Thor
  default_task :map

  desc "map PATH", "Extract EXIF GPS data from images and generate an interactive map"
  method_option :output, aliases: "-o", type: :string, default: "map.html",
                desc: "Output HTML file name"
  method_option :no_open, type: :boolean, default: false,
                desc: "Do not open the generated map automatically"
  def map(path)
    unless File.exist?(path)
      say "Error: Path '#{path}' does not exist.", :red
      exit 1
    end

    image_files = collect_images(path)
    if image_files.empty?
      say "No supported image files found.", :yellow
      exit
    end

    say "\n   Found #{image_files.length} image(s). Extracting EXIF data...\n".bold

    photo_data, skipped_files = extract_exif(image_files)

    say "\n   Processed #{photo_data.length} photo(s) with GPS, skipped #{skipped_files.length} photo(s).".green
    if skipped_files.any?
      say "   Skipped files:".yellow
      skipped_files.each { |f| say "   - #{f}".light_black }
    end

    if photo_data.empty?
      say "\n   No GPS data found. No map will be generated.", :red
      exit
    end

    output_file = options[:output]
    generate_map(output_file, photo_data)

    say "\n   Map generated: #{output_file}".green.bold
    open_map(output_file) unless options[:no_open]
  end

  private

  IMAGE_EXTENSIONS = %w[.jpg .jpeg .tif .tiff .png]

  def collect_images(path)
    if File.directory?(path)
      Dir.glob(File.join(path, '**', '*')).select do |file|
        File.file?(file) && IMAGE_EXTENSIONS.include?(File.extname(file).downcase)
      end
    else
      ext = File.extname(path).downcase
      IMAGE_EXTENSIONS.include?(ext) ? [path] : []
    end
  end

  def extract_exif(files)
    photo_data = []
    skipped = []

    files.each do |file|
      begin
        exif = case File.extname(file).downcase
               when '.jpg', '.jpeg' then EXIFR::JPEG.new(file)
               when '.tif', '.tiff' then EXIFR::TIFF.new(file)
               else nil
               end

        if exif && exif.gps && exif.gps.latitude && exif.gps.longitude
          data = {
            file: file,
            latitude: exif.gps.latitude,
            longitude: exif.gps.longitude,
            datetime: exif.date_time_original || exif.date_time_digitized || exif.date_time,
            make: exif.make,
            model: exif.model,
            exposure_time: exif.exposure_time,
            f_number: exif.f_number,
            iso: exif.iso_speed_ratings,
            focal_length: exif.focal_length
          }
          photo_data << data
          say "  #{File.basename(file)} (#{data[:latitude].round(5)}, #{data[:longitude].round(5)})".green
        else
          skipped << file
          say "  #{File.basename(file)} (no GPS data)".yellow
        end
      rescue => e
        skipped << file
        say "  #{File.basename(file)} (error: #{e.message})".red
      end
    end

    [photo_data, skipped]
  end

  def generate_map(output_file, photo_data)
    template = <<-ERB
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>pollen</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>
    body { margin: 0; padding: 0; }
    #map { position: absolute; top: 0; bottom: 0; width: 100%; }
    .popup-img { max-width: 200px; max-height: 150px; display: block; margin-bottom: 5px; }
  </style>
</head>
<body>
  <div id="map"></div>
  <script>
    var map = L.map('map').setView([<%= photo_data.first[:latitude] %>, <%= photo_data.first[:longitude] %>], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    var photoData = <%= photo_data.to_json %>;

    photoData.forEach(function(photo) {
      var popupContent = '';
      if (photo.file) {
        popupContent += '<img class="popup-img" src="file://' + photo.file.replace(/\\\\/g, '/') + '" alt="Photo">';
      }
      popupContent += '<b>' + (photo.datetime || 'Unknown date') + '</b><br>';
      if (photo.make) popupContent += 'Camera: ' + photo.make + ' ' + (photo.model || '') + '<br>';
      if (photo.exposure_time) popupContent += 'Exposure: ' + photo.exposure_time + 's<br>';
      if (photo.f_number) popupContent += 'Aperture: f/' + photo.f_number + '<br>';
      if (photo.iso) popupContent += 'ISO: ' + photo.iso + '<br>';
      if (photo.focal_length) popupContent += 'Focal length: ' + photo.focal_length + 'mm<br>';

      L.marker([photo.latitude, photo.longitude])
        .addTo(map)
        .bindPopup(popupContent);
    });
  </script>
</body>
</html>
    ERB

    File.write(output_file, ERB.new(template).result(binding))
  end

  def open_map(file)
    if RUBY_PLATFORM =~ /darwin/
      system("open", file)
    elsif RUBY_PLATFORM =~ /linux/
      system("xdg-open", file)
    elsif RUBY_PLATFORM =~ /mswin|mingw|cygwin/
      system("start", "", file)
    else
      say "Please open #{file} manually.", :yellow
    end
  end
end

ExifMap.start(ARGV)