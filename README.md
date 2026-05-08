===========HEDGE-2 GROUND STATION===========

              .%%%%....#..%.%%.              
           .%%%%%--###.=##--%%%%%.           
         .#%%%######.-=-+######=%%%.         
        %%%-#######+-.#.-+#######-%%%.       
      ..:%########+-#.+..-+###.####%%%.      
     .:.-#######:=-=:...:=-=.#######-%..     
     %%%#######+=--=.....=--+=#######=-%     
    #%.#######=+--...:::...--++#######%%%    
    %%%######+=-.:+++#+#*+*#.-==.##.##%%%    
    %%+####.=+-##=+##++#++#=#:--+=####-%=    
    %#%###+=--##==:........==*#--++###%%%    
    .%%##+=---#+#...........+##---=+.#%%%    
     %%%=+----##...-:...#==..+#----=+-%%     
     .%%------#+=+..-----..#++#=-----%%.     
      .%%%---=#+..*..##-.....*+=---=%%.      
        %%%-==+..............*:#=-%%%        
         .%%%-.%.%%%.%%#...%%%.%%%%.         
            .%%.%.%%.......-%%%.%-           
            .  .%.%%%.%%.%.%%. .             
                    %% %%%%                                 

A ground station application for receiving and displaying telemetry data from HEDGE-2.
Version 1.0.0

Patch Notes:
- 1.0.0: Created application

Requirements:
- Windows 10/11
- XBee USB driver installed (install XCTU if unsure)
- Internet connection (for map tiles)

Installation:
1. Extract the ZIP file
2. Place it in a folder where you have write permissions (e.g. Desktop, Documents)
3. Run the executable (either from the shortcut or from the actual EXE in the "dist" folder)
	- Windows may show a SmartScreen warning, click "More info → Run anyway"

Usage:
1. Plug in the XBee receiver via USB
2. Click the refresh button (⟳) to scan for available ports
3. Select the correct port from the dropdown
4. Click "Connect" to begin receiving data
- Live telemetry (latitude, longitude, altitude, velocity) will appear at the top
- The map will update with the payload's current position
- Sensor readings will populate the table below the map

Exporting Data:
- Click "Export to Excel" after disconnecting to save collected data
- Supports .xlsx, .csv, and .txt formats

Notes:
- Do not move the executable while it is running
- tile_cache.db will be created in the same folder as the EXE file (in the dist folder) to cache map tiles for offline use
- Data is lost if the application is closed without exporting