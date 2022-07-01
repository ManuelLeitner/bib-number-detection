sudo apt-get update
sudo apt-get install -y software-properties-common
sudo add-apt-repository -y ppa:alex-p/tesseract-ocr
sudo apt-get update
sudo apt-get install -y tesseract-ocr
wget https://github.com/tesseract-ocr/tessdata/blob/main/tam.traineddata
sudo mv tam.traineddata /usr/share/tesseract-ocr/4.00/tessdata/
sudo pip install pyocr
echo "tesseract-ocr installed successfully"