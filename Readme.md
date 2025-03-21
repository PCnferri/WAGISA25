# Pierce County Tax Parcel Finder Tool, WAGISA 2025
Credits: Natalie Ferri and Cort Daniel

# Introduction
Pierce County Spatial Services provides employees access to six enterprise mapping applications. Most use CountyView Web (CVWeb) for basic mapping, but some, like Assessor-Treasurer appraisers, require ArcGIS Pro for advanced customization. Over the summer, 30 appraisers transitioned from CVWeb to ArcGIS Pro through a three-week training program. One challenge was executing table joins to the tax parcel feature class, a function previously available as a tool in CVWeb. To address this, the TaxParcel Finder Tool was developed in ArcGIS Pro, streamlining parcel selection, exporting data, and adding custom layers. Though designed for appraisers, the tool can be adapted for various Excel-based workflows.

# Tax Parcel Finder Tool’s Python Code
## Part 1: Set Environment & Check Variables 
The script, integrated into an ArcGIS Pro toolbox, allows users to modify settings via an interface. It imports essential libraries (arcpy, os, getpass) and sets input/output paths. Default GeoJSONoutput is saved to a temporary folder but can be redirected. The script verifies the required “Parcels” layer and ensures the TaxParcelNumber field in Excel matches the layer. Errors are flagged if inconsistencies exist. User initials and date are appended to file names for easy identification.

    import arcpy, os, time, getpass
    from datetime import datetime
    
    # Define paths and variables
    gdb_path = arcpy.env.workspace  # User's default GDB
    excel_file = arcpy.GetParameterAsText(0)  # Input Excel file from user
    scratch_geojson = arcpy.GetParameterAsText(1)  # Path for GeoJSON output
    parcels_layer = "Parcels"  # Name of the parcels layer
    field_to_join = "TaxParcelNumber"  # Field to join on
    
    # Check that Parcels is active on map
    stopProcess = False
    
    if not arcpy.Exists(parcels_layer):
            arcpy.AddError(' The ATR > PARCELS feature class is missing '.format(parcels_layer))
            stopProcess = True
        
    if stopProcess:
            arcpy.AddError(' Missing required feature class: {} '.format(parcels_layer))
            arcpy.AddError('!!! Rerun the tool after adding Parcels to the map. ') 
            sys.exit('Missing required feature class or classes.  Stopping process.')
            
    # Function to check field schema
    def check_field_schema(layer, field):
        fields = [f.name for f in arcpy.ListFields(layer)]
        if field not in fields:
            arcpy.AddError(f"Field '{field_to_join}' not found in layer '{excel_file}'. Rename the parcel field in the Excel to include TaxParcelNumber.")
            return False
        return True
    
    # Function for user's initials
    
    def getUserInitials(currentEditor):
        editor = currentEditor.upper().replace('AD\\','') #Active Directory
        
        # Note: Any additional editor exceptions need to be in upper case.
        if editor == 'JCHO':
            editorInitials = 'KC'
        else: 
            editorInitials = editor[:2]  # The string function to get the first two chars of users' login.
        return editorInitials
    
    currentEditor = getpass.getuser()  # User's login name
    userInitials = getUserInitials(currentEditor)
    
    print('currentEditor: {}'.format(currentEditor))
    print('userInitials: {}'.format(userInitials))
      
## Part 2: Join Tax Parcels & Export Features 
The script joins Excel data to the Parcels layer, selects parcels with matching TaxParcelNumber, and exports them as a feature class in the user's geodatabase. Since Pierce County ArcGIS Pro users are not authorized to publish data online, a GeoJSON output is also created for use in FieldMaps on iPads during assessments. The selection is then cleared for the next operation.

    # Creating new outputs
    try:
        # Step 1: Remove previous join
        arcpy.RemoveJoin_management(parcels_layer)
    
        # Step 2: Check schema for the tax parcel number field
        arcpy.AddMessage('Checking schema for TaxParcelNumber field...')
        if not check_field_schema(excel_file, field_to_join):
            raise Exception("Schema check failed. Aborting process. Correct the Excel to include 'TaxParcelNumber'.")
    
        # Step 3: Add join to Parcels layer
        arcpy.AddMessage('Joining table to Parcels...')
        arcpy.AddJoin_management(parcels_layer, field_to_join, excel_file, field_to_join)  # Perform join operation
    
        # Step 4: Select by attribute on Parcels for the joined field
        arcpy.AddMessage('Selecting joined Parcels...')
        joined_field = f"{os.path.splitext(os.path.basename(excel_file))[0]}.{field_to_join}"  # Build joined field name
        expression = f"{joined_field} IS NOT NULL"  # Selection criteria
        arcpy.SelectLayerByAttribute_management(parcels_layer, "NEW_SELECTION", expression)  # Execute selection
    
        # Step 5: Export selected Parcels to user's default GDB
        arcpy.AddMessage('Exporting selected Parcels to GDB...')
        output_name = f"Parcels_{userInitials}_{datetime.now().strftime('%m%d%y_%H%M')}"  # Generate output name with user initials and timestamp
        output_gdb = os.path.join(gdb_path, output_name)  # Construct output path
        arcpy.CopyFeatures_management(parcels_layer, output_gdb)  # Copy selected features to GDB
    
        # Step 6: Export selected Parcels to GeoJSON
        arcpy.AddMessage('Converting features to GeoJSON...')
        geojson_path = os.path.join(scratch_geojson, f"Parcels_{userInitials}_{datetime.now().strftime('%m%d%y_%H%M')}.geojson")  # GeoJSON output path
        
        arcpy.FeaturesToJSON_conversion(
            output_gdb,
            geojson_path,
            format_json="NOT_FORMATTED",
            include_z_values="NO_Z_VALUES",
            include_m_values="NO_M_VALUES",
            geoJSON="GEOJSON",
            outputToWGS84="KEEP_INPUT_SR",
            use_field_alias="USE_FIELD_NAME"
            ) 
    
        # Step 7: Clear selection from Parcels
        arcpy.SelectLayerByAttribute_management(parcels_layer, "CLEAR_SELECTION")  # Clear any previous selections

## Part 3: Add Parcels to Map, Symbolize & Label 
The newly created feature class is added to the map with a bright pink outline and labels for easy identification. The script zooms to the selected layer, then clears the selection to enhance visibility on dark orthophotography basemaps. Appraisers can further customize their maps with additional symbology and labeling.

       # Step 8: Add new parcels layer to the map
          arcpy.AddMessage('Adding service area parcels to map...')
          aprx = arcpy.mp.ArcGISProject('CURRENT')  # Get the current ArcGIS project
          current_map = aprx.activeMap  # Reference the active map
          current_map.addDataFromPath(output_gdb)  # Add the new layer to the map
      
          # Step 9: Apply bright pink symbology to the new layer    
          newparcels = os.path.basename(output_gdb)  # Get the name of the new parcels layer
          aprx = arcpy.mp.ArcGISProject('CURRENT')  # Get the current project
          activemap = aprx.activeMap  # Get the active map
          lyr = activemap.listLayers(newparcels)[0]  # Reference the new layer
          sym = lyr.symbology  # Get the current symbology
          
          # Symbology characteristics 
          sym.renderer.symbol.applySymbolFromGallery("Extent Transparent Wide Gray")  # Apply a predefined symbol
          sym.renderer.symbol.color = {'RGB' : [0, 0, 0, 0]}  # Set symbol color
          sym.renderer.symbol.outlineColor = {'RGB' : [255, 19, 240, 100]}  # Set outline color to bright pink
          sym.renderer.symbol.size = 2  # Set symbol size
          lyr.symbology = sym  # Update layer with new symbology
          arcpy.AddMessage('Symbology applied to new parcels layer.')
      
          # Adding labels
          lyr = activemap.listLayers('Parcels_*')[0]
          sym = lyr.symbology
          lblClass = lyr.listLabelClasses('Class 1')[0]
          lblClass.expression = '$feature.GDB_Parcel_TaxParcelNumber'
          lyr.showLabels = True
              
          # Step 10: Zoom to the extent of the new layer
          arcpy.AddMessage('Zooming to the new parcels layer extent...')
          expression = "GDB_Parcel_TaxParcelNumber IS NOT NULL"  # Selection criteria
          arcpy.SelectLayerByAttribute_management(newparcels, "NEW_SELECTION", expression)  # Execute selection
          df = aprx.activeView
          df.zoomToAllLayers(True) # Zoom to selection
          time.sleep(2) # Pause for effect
          arcpy.SelectLayerByAttribute_management(newparcels, "CLEAR_SELECTION")  # Clear previous selection

## Part 4: Inform Users of Data Location
Users receive a notification of the feature class andGeoJSON file name and locations. The process, which takes about 30 seconds to execute, significantly improves efficiency compared to manual operations.

        # Step 11: Notify Users of the output locations
            arcpy.AddMessage('---------------------------------')
            arcpy.AddMessage('Finished!')
            arcpy.AddMessage(f'Parcels added to map are located at: {output_gdb}')
            arcpy.AddMessage(f'Parcels geoJSON file located at: {geojson_path}')
            arcpy.AddMessage('---------------------------------')
        
        except Exception as e:
            arcpy.AddError(str(e))  # Log any errors that occur during processing
        finally:
            arcpy.AddMessage('Process completed.')  # Notify completion of the process

# Conclusion
This tool helped the Pierce County appraisers transition smoothly to ArcGISPro, enhancing parcel review and pre-site assessments. Python continues to enhance GIS workflows, saving time and simplifying complex tasks.

Whether your teams are working with large datasets or performing routine tasks, Python can be a powerful tool to navigate complex geospatial work, establish efficiencies, and help users feel empowered while using ArcGIS Pro. 

# About Pierce County
Pierce County, home to 946,000 residents, spans 1,670 square miles. The Pierce County Assessor-Treasurer’s appraisers conduct physical assessments across 27 cities and towns, completing 55,000 residential assessments annually.

Pierce County IT-Spatial Services supports 1,000+ GIS users, maintaining geospatial applications, datasets, and asset management tools essential for county operations.
