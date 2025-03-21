"""Pierce County ATR Appraiser Parcel Select Tool

This tool replicates the Import Parcel Table tool from CountyView Web.

Steps:
1. Remove previous join from PARCELS layer 
2. Schema checker 
3. Add join to PARCELS layer on taxparcelnumber field using an xlsx file provided by the user
4. Select attributes in PARCELS for joined tax parcel number field where xlsxjoinedfield.taxparcelnumber is not null
5. Export selected PARCELS to user's default GDB, named Parcels_initials_date_time
6. Export selected PARCELS to scratch drive as Parcels_initials_date_time.geojson
7. Add parcels_date_time as a layer to the map
8. Clear selection from PARCELS
9. Apply bright pink symbology to new layer with labels
10. Zoom to new layer extent 
11. Notify user of output locations

Creators: Natalie Ferri, Cort Daniel
Created: 10/8/24
"""

import arcpy, os, time, getpass
from datetime import datetime

# Define paths and variables
gdb_path = arcpy.env.workspace  # User's default GDB
excel_file = arcpy.GetParameterAsText(0)  # Input Excel file from user
scratch_geojson = arcpy.GetParameterAsText(1)  # Path for GeoJSON output
parcels_layer = "Parcels"  # Name of the parcels layer
field_to_join = "TaxParcelNumber"  # Field to join on

# Check that ATR's Parcels is active on map
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

# Creating new outputs
try:
    # Step 1: Remove previous join
    arcpy.RemoveJoin_management(parcels_layer)

    # Step 2: Check schema for the tax parcel number field
    arcpy.AddMessage('Checking schema for TaxParcelNumber field...')
    if not check_field_schema(excel_file, field_to_join):
        raise Exception("Schema check failed. Aborting process. Correct the Excel to include 'TaxParcelNumber'.")

    # Step 3: Add join to parcels layer
    arcpy.AddMessage('Joining table to Parcels...')
    arcpy.AddJoin_management(parcels_layer, field_to_join, excel_file, field_to_join)  # Perform join operation

    # Step 4: Select by attribute on parcels for the joined field
    arcpy.AddMessage('Selecting joined Parcels...')
    joined_field = f"{os.path.splitext(os.path.basename(excel_file))[0]}.{field_to_join}"  # Build joined field name
    expression = f"{joined_field} IS NOT NULL"  # Selection criteria
    arcpy.SelectLayerByAttribute_management(parcels_layer, "NEW_SELECTION", expression)  # Execute selection

    # Step 5: Export selected parcels to user's default GDB
    arcpy.AddMessage('Exporting selected Parcels to GDB...')
    output_name = f"Parcels_{userInitials}_{datetime.now().strftime('%m%d%y_%H%M')}"  # Generate output name with user initials and timestamp
    output_gdb = os.path.join(gdb_path, output_name)  # Construct output path
    arcpy.CopyFeatures_management(parcels_layer, output_gdb)  # Copy selected features to GDB

    # Step 6: Export selected parcels to GeoJSON
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

    # Step 7: Clear selection from parcels
    arcpy.SelectLayerByAttribute_management(parcels_layer, "CLEAR_SELECTION")  # Clear any previous selections

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
