import psycopg2

def create_spatial_index():
    # Database configuration
    DB_NAME = "weather_forecast_map"
    DB_USER = "x"
    DB_PASSWORD = ""
    DB_HOST = ""
    DB_PORT = "5432"
    
    conn = None
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()
        
        # Create spatial index
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_districts_geom 
        ON districts 
        USING GIST(geom);
        """)
        
        # Commit the transaction
        conn.commit()
        print("Spatial index created successfully")
        
    except Exception as e:
        print(f"Error creating index: {e}")
        
    finally:
        if conn:
            cursor.close()
            conn.close()

if __name__ == "__main__":
    create_spatial_index()
