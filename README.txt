#Steps to install on AWS REBL OS
$sudo yum -y update
$sudo yum -y install yum-utils
$wget https://www.python.org/ftp/python/3.7.9/Python-3.7.9.tar.xz
$tar xf Python-3.* 
$cd Python-3.*
$./configure --prefix=/usr/local/python3 >>>> if you face error install development Tool cmd in below step
$yum groupinstall "Development Tools"
$make
$make altinstall
### if above install doesn't work follow below steps
$sudo yum list | grep python3
$sudo yum install python3.x86_64

#### SET ENV VAR ###
$which python
#/usr/bin/python <<<<<< this might be your current path for older python(Existing version)
$vi ~/.bash_profile  
#alias python='/usr/local/python3/bin/python3.7' <<<<<< add this in the file
$source ~/.bash_profile <<<< Reloads the bash_profile
$python --version <<<<< Confirm the version
#Python 3.7.9

#Note: after python instllation check ur setantenv and ant clean all
#   if java home doesn't work or refers to different path... add the below command
#   as the first line in these files setantenv.sh and hybrisserver.sh 
$export JAVA_HOME="/usr/java/jdk1.8.0_201-amd64" <<<<< add you java path like this

#Python packages required
$sudo pip3 install Flask
$sudo pip3 install Flask_cores
$sudo pip3 install psutil
$sudo pip3 install Pandas
$sudo pip3 install mysql-connector-python <<< install based on DB type
#change to executable mode
$chmod u+x validate.sh

#Run the script
$./validate.sh 