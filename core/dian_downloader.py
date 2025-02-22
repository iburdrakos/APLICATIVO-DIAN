from seleniumbase import SB
import time
import os
import logging
import requests

def process_cufe(self, driver, cufe):
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            url = "https://catalogo-vpfe.dian.gov.co/User/SearchDocument"
            logging.info(f"Procesando CUFE: {cufe}")
            
            driver.get(url)
            time.sleep(3)

            logging.info("Esperando CAPTCHA...")
            # Esperar a que el iframe del CAPTCHA esté presente
            wait = WebDriverWait(driver, 10)
            frames = wait.until(EC.presence_of_all_elements_located((By.TAG_NAME, "iframe")))
            
            # Buscar el frame del CAPTCHA
            for frame in frames:
                if "recaptcha" in frame.get_attribute("src").lower():
                    driver.switch_to.frame(frame)
                    # Hacer clic en el checkbox
                    checkbox = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "recaptcha-checkbox-border")))
                    checkbox.click()
                    time.sleep(4)  # Esperar a que se resuelva
                    driver.switch_to.default_content()
                    break

            # Ingresar CUFE
            input_field = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input[placeholder='Ingrese el código CUFE o UUID']")))
            input_field.send_keys(cufe)
            time.sleep(2)

            # Buscar
            search_button = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(text(),'Buscar')]")))
            search_button.click()
            time.sleep(5)

            current_url = driver.current_url
            logging.info(f"URL capturada: {current_url}")

            with open("urls.txt", "a") as file:
                file.write(f"{cufe}: {current_url}\n")

            token = None
            if "Token=" in current_url:
                token = current_url.split("Token=")[1].split("&")[0]
            elif "token=" in current_url:
                token = current_url.split("token=")[1].split("&")[0]

            if token:
                download_url = f"https://catalogo-vpfe.dian.gov.co/Document/DownloadPDF?trackId={cufe}&token={token}"
                response = requests.get(download_url)
                
                if response.status_code == 200:
                    excel_name = os.path.splitext(os.path.basename(self.excel_path))[0]
                    filename = f"{excel_name}_{cufe}.pdf"
                    filepath = os.path.join(self.folder_path, filename)
                    with open(filepath, "wb") as file:
                        file.write(response.content)
                    logging.info(f"Archivo PDF descargado: {filename}")
                    
                    with open(os.path.join(self.folder_path, "links_descarga.txt"), "a") as file:
                        file.write(download_url + "\n")
                else:
                    logging.error(f"Error al descargar el archivo PDF para el CUFE {cufe}")
            else:
                logging.error(f"No se encontró el token en la URL para el CUFE {cufe}")

            return True

        except Exception as e:
            logging.error(f"Error procesando CUFE {cufe}: {str(e)}")
            return False