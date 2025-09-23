import time
from minio import Minio
from datetime import datetime

def test_list_response_time(bucket_name, prefix=""):
    print(f"Testing response time for listing objects in {bucket_name}/{prefix}")

    start_time = time.time()
    objects = list(client.list_objects(bucket_name, prefix=prefix))
    end_time = time.time()
    duration = end_time - start_time
    count = len(objects)

    print(f"Found {count} objects in {duration:.2f} seconds")

    # Only show average if we actually found objects
    if count > 0:
        avg_per_1000 = (duration/count) * 1000
        print(f"Average time per 1000 objects: {avg_per_1000:.2f} seconds")

    # Print first few objects to verify
    for obj in objects[:5]:
        print(f"Sample object: {obj.object_name}")

def monitor_object_appearance(bucket_name, object_prefix, expected_count):
    print(f"Monitoring object appearance in {bucket_name}/{object_prefix}")
    print(f"Expecting {expected_count} objects")

    start_time = time.time()
    previous_count = 0

    while True:
        current_count = sum(1 for _ in client.list_objects(bucket_name, prefix=object_prefix))

        if current_count != previous_count:
            elapsed = time.time() - start_time
            print(f"[{elapsed:.2f}s] Found {current_count}/{expected_count} objects")
            previous_count = current_count

        if current_count >= expected_count:
            break

        time.sleep(0.5)  # Wait half second between checks

    total_time = time.time() - start_time
    print(f"\nAll {expected_count} objects found in {total_time:.2f} seconds")

if __name__ == "__main__":
    # Replace these with your actual MinIO credentials
    client = Minio(
        "devdocker01.cofidis.pt:10024",  # Replace with your MinIO server address
        access_key="minioadmin",  # Replace with your access key
        secret_key="minioadmin123",  # Replace with your secret key
        secure=False  # Set to True if using HTTPS
    )

    bucket_name = "storage"

    # First, verify bucket exists and we can connect
    try:
        if not client.bucket_exists(bucket_name):
            print(f"Error: Bucket '{bucket_name}' does not exist!")
            exit(1)
        print(f"Successfully connected to MinIO and found bucket '{bucket_name}'")
    except Exception as e:
        print(f"Error connecting to MinIO: {e}")
        exit(1)

    # Test each directory
    for prefix in ["input/", "output/", "backup/"]:
        print(f"\n=== Testing {prefix} directory ===")
        test_list_response_time(bucket_name, prefix)

    print("\n=== Testing real-time object detection ===")
    monitor_object_appearance(bucket_name, "input/", 10000)
