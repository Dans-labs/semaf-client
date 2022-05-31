# semaf-client
SEMAF python client to manage Linked Data in FAIR data repositories

# Installation
```
git clone https://github.com/Dans-labs/semaf-client
git checkout cmdi
pip3 install -r requirements.txt
cp ./config.default.py config.py
```
Fill your configuration parameters for Dataverse in config.py and run demo conversion
```
python3 ./semaf-demo.py ./0b01e4108004e49d_INV_REG_REPARATIE_CONSUMENTENARTIKELEN_HANDEL_2008-01-01.dsc
```
