import requests
from requests import HTTPError
from bs4 import BeautifulSoup
import os
import pymysql

score_baseurl = r'http://jwgl.ynau.edu.cn:9000/bysh/jdDetail.aspx?xh='
photo_baseurl = r'http://jwgl.ynau.edu.cn/stuphoto/'

def getStudent(year):
    guessSnoList = []
    snoList =[]
    txtFilePath = os.path.join(os.path.abspath(os.path.curdir),str(year)+'.txt')

    if os.path.exists(txtFilePath):
        with open(txtFilePath,'r') as f:
            for line in f:
                snoList.append(line.strip())
        return snoList

    year = str(year) + '31'

    for s in range(5000):
        guessSnoList.append(year+str(s).zfill(4))
        
    for sno in guessSnoList:
        r = requests.get(photo_baseurl+sno+'.jpg')
        print(r.status_code)
        if r.status_code == 200:
            snoList.append(sno)

    with open(txtFilePath,'w') as f:
        for sno in snoList:
            f.writelines(sno+'\n')

    return snoList


def getScore(year):
    snoList = getStudent(year)
    nowIndex = 0 #当前进度
    
    AllStudent = [] #所有学生的课程信息 每项都是一个aStudentAllCourse字典
    AllCourse = {} #所有的课程信息 key：课程编号 value：课程信息列表[课程名称，总人数，总成绩，平均成绩，不及格人数]

    for student in snoList:
        aStudentAllCourse = {} #某学生所有的课程 key：课程编号  value：课程信息列表[课程名称，成绩]
        try:
            r = requests.get(score_baseurl+str(student))
            obj = BeautifulSoup(r.text)
        except HTTPError as e:
            print(e)
        
        try:
            scoreTable = obj.findAll('table')[1] #成绩表格
            scores = scoreTable.findAll('tr')
            for i in range(1,len(scores)-1): #去掉表头表尾
                score = scores[i].findAll('td') #某行成绩
                id = score[0].text
                info = [score[1].text,float(score[5].text)]
                aStudentAllCourse[id] = info
        
            for id,info in aStudentAllCourse.items():
                if id in AllCourse: #如果该课程已经存在了，则将该课程的数据相加
                    oldInfo = AllCourse[id]
                    oldInfo[1] = oldInfo[1] + 1 #人数加1
                    oldInfo[2] = oldInfo[2] + aStudentAllCourse[id][1] #总成绩相加
                    if aStudentAllCourse[id][1] < 60:
                        oldInfo[4] = oldInfo[4] + 1
                else:#如果该课程不存在，则添加该课程
                    oldInfo = []
                    oldInfo.append(aStudentAllCourse[id][0])
                    oldInfo.append(1)
                    oldInfo.append(aStudentAllCourse[id][1])
                    oldInfo.append(0.0)
                    oldInfo.append(0)
                    if aStudentAllCourse[id][1] < 60:
                        oldInfo[4] = 1
                    AllCourse[id] = oldInfo
            
        except AttributeError as e:
            print(e)
        
        else:
            nowIndex = nowIndex + 1
            print('已完成%d/%d'%(nowIndex,len(snoList)))

    for id,info in AllCourse.items():
        info[3] = info[2]/info[1]

    return AllCourse

        
if __name__=='__main__':
    AllCourse = getScore(2014)
    nowIndex = 0
    conn = pymysql.connect(host='127.0.0.1',user='root',passwd='wshyb1996',db='mysql',charset='utf8')
    cur = conn.cursor()
    cur.execute('USE Score')
    for id,info in AllCourse.items():
        cur.execute('INSERT INTO 2014score(id,name,average_score,student_num,pass_rate) VALUES("%s","%s","%s","%s","%s")',(int(id),info[0],info[3],info[1],info[4]/info[1]))
        nowIndex = nowIndex + 1
        print('正在向数据库写入数据(%d/%d)'%(nowIndex,len(AllCourse)))
    cur.connection.commit()
    cur.close()
    conn.close()
    print('数据写入完成。')