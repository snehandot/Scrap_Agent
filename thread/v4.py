import time
import threading
from queue import Queue
from selenium import webdriver
from selenium.webdriver.common.by import By
from multiprocessing import Process, Queue as MPQueue

driver_dict={}

# Queue to store button values
button_queue = Queue()

def scroll_and_load(driver, wait_time=2):
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(wait_time)  # Wait for new content to load
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

def find_elements(driver, tags):
    elements = []
    for tag in tags:
        elements.extend(driver.find_elements(By.TAG_NAME, tag))
    return elements

def collect_clickable_elements(driver):
    tags = ["button", "input", "a"]
    elements = find_elements(driver, tags)
    return elements

script = """
function getVisibleText(element) {
    return element.innerText.trim();
}
var elements = arguments[0];
var result = [];
elements.forEach(function(element) {
    var elementInfo = {
        tagName: element.tagName,
        visibleText: getVisibleText(element),
    };
    result.push(elementInfo);
});
return result;
"""

def get_elements_info(driver, elements):
    return driver.execute_script(script, elements)

def scrape_buttons(url, queue, unique_id):
        driver = webdriver.Chrome()
        driver_dict[unique_id] = driver  
        driver.get(url)
        scroll_and_load(driver, wait_time=4)
        clickable_elements = collect_clickable_elements(driver)
        elements_info = get_elements_info(driver, clickable_elements)
        
        # Filter out elements without visible text and remove duplicates
        seen_elements = set()
        unique_elements_info = []

        for element_info in elements_info:
            key = (element_info['visibleText'], element_info['tagName'])
            if key not in seen_elements:
                seen_elements.add(key)
                unique_elements_info.append(element_info)
        
        visible_texts = [element_info['visibleText'] for element_info in unique_elements_info if element_info['visibleText']]
        driver.quit()
        
        # Put the collected button values into the queue
        queue.put((unique_id, visible_texts))


def process_buttons(mp_queue,mp_queue_from_llm):
    while True:
        if not mp_queue.empty():
            unique_id, buttons = mp_queue.get()
            # Placeholder for LLM processing (replace with actual LLM call)
            result = f"button for {unique_id}"  # Simulate processing


            print(f"LLM process done for Processed result for {unique_id}: {result}")
            mp_queue_from_llm.put((unique_id, result))

def queue_listener(mp_queue_from_llm):
    while True:
        response = mp_queue_from_llm.get()  # Blocking call, waits for an element
        if response is None:  # Sentinel value to stop the listener
            break
        unique_id, result = response  # Unpack the tuple

        # Create and start a worker thread
        thread = threading.Thread(target=worker_function, args=(unique_id,result))
        thread.start()

def worker_function(unique_id,result):
    """Function to be executed by each worker thread."""
    # Simulate some work
    time.sleep(0.2)
    print(f"CLick executed: {unique_id} and {result}")
    


# Main function to start WebDriver threads and the LLM process
def main():
    urls = [
    "https://www.flipkart.com",
    "https://www.ajio.com",
    "https://www.myntra.com"
     ]
    # Multiprocessing queue to communicate with LLM process
    mp_queue_from_llm = MPQueue()
    mp_queue = MPQueue()


    #The driver objects will be inistialised into dictionary here
    threads = []
    for i, url in enumerate(urls):
        unique_id = f"driver_{i}"
        thread = threading.Thread(target=scrape_buttons, args=(url, mp_queue, unique_id))
        threads.append(thread)
        thread.start()

    
    

    # LLM Multi Processing
    llm_process = Process(target=process_buttons, args=(mp_queue,mp_queue_from_llm))
    llm_process.start()

    listener_thread = threading.Thread(target=queue_listener, args=(mp_queue_from_llm,))
    listener_thread.start()



    

    # Wait for all threads to complete
    for thread in threads:
        thread.join() 

    mp_queue_from_llm.put(None)

    # Wait for the listener thread to finish
    listener_thread.join()

    # Ensure LLM process is terminated after processing
    llm_process.terminate()
    llm_process.join()

if __name__ == "__main__":
    main()

