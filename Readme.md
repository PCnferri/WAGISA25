# Pierce County Tax Parcel Finder Tool, WAGISA 2025
Credits: Natalie Ferri and Cort Daniel

# Introduction
Pierce County Spatial Services provides employees with access to and training on six enterprise mapping applications. Most employees use CountyView Web (CVWeb), a web-based application that offers a built-in data menu, basic query and analysis tools, layer customization, and print functionality. While CVWeb satisfies most mapping needs, some users require the advanced capabilities of ArcGIS Pro. For example, the Assessor-Treasurer’s commercial and residential appraisers use CVWeb to review assigned tax parcels before physical assessments. However, due to the need for more advanced layer and labeling customization, a migration to ArcGIS Pro was requested. 

Over the summer, Pierce County Spatial Services helped migrate 30 users from CVWeb to ArcGIS Pro. To facilitate this transition, a specialized three-week training program was developed and delivered to three groups of ten. One challenge during training involved a key aspect of the appraisers' workflow that had previously been automated: identifying assigned tax parcels from an Excel table. In CVWeb, the “Import Tax Parcel Table” tool allows users to upload an Excel table then automatically zooms to the tax parcels, highlights them, and creates a GeoJSON output. The appraisers were trained in ArcGIS Pro on how to join a table to a layer, select the joined tax parcels, and zoom to the layer. However, this process proved to be time-consuming and confusing for beginners.

To address this challenge, the Tax Parcel Finder tool was developed for ArcGIS Pro to automate this process. The Python script uses an imported Excel table to join to an existing layer, exports the tax parcels as both a feature class and GeoJSON, and adds the new feature class as a map layer with custom symbology. It then zooms to the newly added layer. Although this tool was designed for a specific user group, it can be adapted for use with any feature from an Excel table.

# Tax Parcel Finder Tool’s Python Code
## Part 1: set the environment and check variables 
The code was initially written as a Python script and then integrated into an ArcGIS Pro toolbox as a script, allowing users to interact with variables directly through the tool's interface. Users can easily edit, open, and run the tool by right-clicking on its script icon.

The script starts by importing important libraries: arcpy for GIS tasks, os for working with file paths, and getpass for user authentication. Next, it defines the paths for input and output data. In this case, the input variable is an Excel file (0), the output variable is a GeoJSON file (1), and the user’s default geodatabase is used for a feature class output. These paths are set as variables in the tool interface. To reduce long-term data storage costs, the GeoJSON default output location will save to a folder that deletes data after seven days. However, since the tool is interactive, the user can redirect the storage location of the GeoJSON to their preferred location.

The script then checks if the required "Parcels" layer is available on the map. It also verifies that the "TaxParcelNumber" field exists in the input Excel file and matches the corresponding field in the parcels layer. If the layer is missing or the fields don’t match, the script raises an error and stops running. This step helps prevent problems later by ensuring that the data structures are correct from the start.

Lastly, the script uses the client directory database to generate the user’s initials for the output’s naming convention. Since the GeoJSON output is saved to a shared location, initials help each user know which GeoJSON is theirs. 

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
      
## Part 2: join tax parcels to layer and export features 
Once the schema is validated, the script joins the Excel data with the Parcel layer using the "TaxParcelNumber" field, creating a combined dataset. It then selects the tax parcels from the Pierce County layer where the joined  "TaxParcelNumber" is not null. This selection is exported as a feature class to the user’s default geodatabase, allowing the user to edit the data and add notes during pre-site assessments.

Since Pierce County ArcGIS Online users are not authorized to publish data, appraisers also need a GeoJSON output to upload the assigned tax parcels to ArcGIS Online. This GeoJSON layer will be referenced using Fieldmaps on iPads during physical assessments. After generating the outputs, the selection is cleared in preparation for a new one.

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

## Part 3: add identified tax parcels to map, symbolize, and label
After the script creates two outputs, it then adds the new feature class as a layer onto the active map. During this segment of the process, customization is automated by applying a bright pink outline and labels for easy visualization and identification. To make this process more user-friendly, the script makes another selection of the tax parcels to then zoom to the layer’s extent. To make the bright pink outline more visible, a final clear selection is performed to remove the blue highlight indicator. 

It was essential to use a vibrant color for the symbology to clearly distinguish tax parcel lines in the darker areas of the orthophotography basemap, such as waterways. Many appraisers will further enhance their maps with additional symbology and customized labeling.

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

## Part 4: inform user of where to find their data
The final step of the process involves notifying the user of the names of their feature class and GeoJSON files, as well as providing the location to access them. The script then concludes the Try statement, signaling the end of the process. Overall, the task takes approximately 30 seconds to complete, which is a significant time savings compared to performing the steps manually. 

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

This streamlined process was highly effective in overcoming a major obstacle during the Pierce County Assessor-Treasurer appraiser’s transition from CountyView Web to ArcGIS Pro. Since the initial training, a follow-up session was held to reinforce the previously covered workflows and address any additional questions. As a result, the commercial and residential appraisers are now confidently using ArcGIS Pro to review assigned tax parcels in their service areas and carry out critical tasks before conducting physical site assessments.

Whether your teams are working with large datasets or performing routine tasks, Python can be a powerful tool to navigate complex geospatial work, establish efficiencies, and help users feel empowered while using ArcGIS Pro. 

# About Pierce County
Pierce County is home to 946,000 residents living within 1,670 square miles. Pierce County government operates with 3,855 employees who help make Pierce County a great place to work, play, and raise a family. 

The Pierce County Assessor-Treasurer’s commercial and residential appraisers perform physical site assessments throughout Pierce County, including in 27 cities and towns. During an assessment cycle, the residential appraisers will complete on average 55,000 physical assessments over 9 months. 

Pierce County IT-Spatial Services designs, develops, and maintains geographic information systems, geospatial applications, spatial datasets, and asset management software to support 1,000+ GIS and asset management users throughout Pierce County government.
