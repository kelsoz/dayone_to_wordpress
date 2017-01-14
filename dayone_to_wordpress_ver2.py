#coding:utf-8

import json,sys,mistune,os,md5,datetime,webbrowser
from wordpress_xmlrpc import Client, WordPressPost, WordPressMedia
from wordpress_xmlrpc.compat import xmlrpc_client
from wordpress_xmlrpc.methods import media, posts


"""
更新日志：
暴力优化了旧文章发表流程

1.直接把图片上传的名字改成了当前日期+时间的格式：20171010-1645
2.旧文章的修改不作 md5 对比，全部删除掉，不管它有没有修改全部重新上传
3.完成后，在browser 里打开网址
"""



#中文乱码
reload(sys)
sys.setdefaultencoding( "utf-8" )

def dayone_have_pic(json_path,entries):
    
    b = False

    photos_path =  os.path.dirname(json_path) + u"/photos/"
    if os.path.exists(photos_path):
        b = True
    else:
        b = False

    photos_info_list = False 
    if entries.has_key('photos'):
        photos_info_list = entries["photos"]
        print "共有配图%s张"%len(photos_info_list)
    else:
        photos_info_list = False 

    if (b and photos_info_list):
        return photos_info_list
    else:
        return False

def get_post_tag(entries):
    post_id = False
    music_url = False
    post_status = "publish"
    post_format = "standard"
    Preset_tag = ["音乐","随手拍","设计","视频","电影","生日","游戏","旅行","教程","推荐","技巧","吉他","代码","败家"]
    if entries.has_key('tags'):
        for tag in entries["tags"]:
            # print "tag:", tag
            if tag[-4:] == ".mp3" or tag[-4:] == ".m4a":
                music_url = tag
            elif tag.startswith("postid"):
                post_id = tag[7:]
            elif len(filter(str.isdigit, tag.encode("utf-8"))) == 4:
                post_id = filter(str.isdigit, tag.encode("utf-8"))
            elif tag == "private" or tag == "p":
                post_status = "private"
            elif tag == "image" or tag == "postformat:image":
                post_format = "image"
            elif tag in Preset_tag:
                wp_post_tag.append(tag)

    return post_id,music_url,post_status,post_format

def new_post_with_pic(content_raw,photos_info_list,post_date):
    
    

    print "处理photo,添加本地路径"
    photos_info_list = add_photos_path(photos_info_list)

    print "上传photo,写入photos_info_list"
    photos_info_list,n = upload_pic_list(photos_info_list)

    print "共上传了%s张图片"%n
    post_content = content_raw[content_raw.find('\n') + 1:]

    #得到特色图片id
    thumbnail_img_id = get_thumbnail_img_id(photos_info_list)

    print "替换里的图片地址为url"
    post_content_markdown = deal_content_raw(post_content,photos_info_list)

    print "转md to html"
    post_content = mistune.markdown(post_content_markdown.encode("utf-8"))

    global music_url
    global wp_post_tag
    if music_url:
        post_content =add_music(post_content,music_url)
        wp_post_tag.append("音乐")

    print "处理标题"
    post_title = content_raw[0:content_raw.find('\n')]
    while post_title[0] == "#":
        post_title = post_title[1:]

    # 上传文章----------------------
    post_id = upload_post(post_title,post_content,img_id =thumbnail_img_id, post_status = post_status,post_date = post_date,post_tag = wp_post_tag,post_format = post_format)

    print "上传成功,post id:",post_id
    return post_id,n

def GetFileList(FindPath,FlagStr=[]):   
    ''''' 
    #检查目录是否有配图，返回图片path_list

    #获取目录中指定的文件名
    #>>>FlagStr=['F','EMS','txt'] #要求文件名称中包含这些字符 
    #>>>FileList=GetFileList(FindPath,FlagStr) # 
    ''' 
    # print FindPath
    if os.path.exists(FindPath):
        FileList=[]
        FileNames=os.listdir(FindPath)
        if (len(FileNames)>0):  
            for fn in FileNames:    
                    
                    if (len(FlagStr)>0):    
                            #返回指定类型的文件名
                            if (FlagStr == fn): 
                                fullfilename=os.path.join(FindPath,fn)  

                                #md5
                                img_md5 = getmd5(fullfilename)

                                file_dirt = {u"file_path":fullfilename,u"md5":img_md5}

                                FileList.append(file_dirt)
                    else:   
                            #默认直接返回所有文件,除去.html以外
                            if (os.path.splitext(fn)[1] == '.jpg' or os.path.splitext(fn)[1] == '.png' or os.path.splitext(fn)[1] == '.JPG' or os.path.splitext(fn)[1] == '.PNG'or os.path.splitext(fn)[1] == '.jpeg'or os.path.splitext(fn)[1] == '.gif'or os.path.splitext(fn)[1] == '.GIF'):
                                # print fn
                                fullfilename=os.path.join(FindPath,fn)
                                # print "fullfilename",fullfilename

                                #md5
                                img_md5 = getmd5(fullfilename)

                                file_dirt = {u"file_path":fullfilename,u"md5":img_md5}

                                FileList.append(file_dirt)
    
        #对文件名排序 
        if (len(FileList)>0):   
                FileList.sort() 
        else:
                return False
    
        return FileList 
    else:
        return False


def getmd5(filename): 
    file_txt = open(filename,'rb').read()  
    m = md5.new(file_txt)  
    return m.hexdigest()

def add_photos_path(dayone_photos_list):
    """
    dayone_photos_list数组里元素格式(dict):

    "fnumber": "(null)", 
    "orderInEntry": 0, 
    "width": 1920, 
    "type": "jpeg", 
    "identifier": "A0CB51BE7EED435A93E23C3BE0886944", 
    "height": 1080, 
    "md5": "e782060a72bc99cb08143e7a70f9b2ca", 
    "focalLength": "(null)"
    "url":False
    """

    photos_path =  os.path.dirname(json_path) + u"/photos/"
    finder_photos = GetFileList(photos_path)

    """
    finder_photos数组里元素格式(dict):
    "file_path":fullfilename,
    "md5":img_md5
    """

    print "对比图片 md5 与 dayone 里的md5"
    for img in dayone_photos_list:
        for finder_img in finder_photos:
            if img["md5"] == finder_img["md5"]:
                img["file_path"] = finder_img["file_path"]
    print "对比完毕"

    print "打印 dayone_photos_list 内容:"
    for x in dayone_photos_list:
        print x

    return dayone_photos_list

def get_time():
    #返回当前时间字符串，格式：20170123
    return datetime.datetime.now().strftime("20%y%m%d-%H%M")

#上传图片
def upload_pic(pic_path,pic_title=[]):
    print "上传图片的路径:",pic_path
    # 准备元数据
    if (len(pic_title)>0):
        data = {
            'name': pic_title + '.jpg', 
            'type': 'image/jpeg',   # mimetype
        }
    else:
        #把图像名命名为当前时间
        img_name = get_time()
        data = {
                        'name': img_name + '.jpg', 
                        'type': 'image/jpeg',   # mimetype
        }
    # 上传，转化成二进制文件
    with open(pic_path, 'rb') as img:
                    data['bits'] = xmlrpc_client.Binary(img.read())

    img_have_upload = client.call(media.UploadFile(data))

    #上传后返回的图像信息
    # img_have_upload == {
    #          'id': 6,
    #          'file': 'picture.jpg'
    #          'url': 'http://www.example.com/wp-content/uploads/2012/04/16/picture.jpg',
    #          'type': 'image/jpeg',
    # }
    pic_id = img_have_upload['id']
    pic_url = img_have_upload['url']
    print "上传图片成功，url:%s    id:%s"%(pic_url,pic_id)
    return pic_url,pic_id

def upload_pic_list(pic_list):
    notification("准备上传图片中,请耐心等待.....","具体时间要看你的图片数量以及网络情况")
    """
    pic_list 数组里元素格式(dict):
    "fnumber": "(null)", 
    "orderInEntry": 0, 
    "width": 1920, 
    "type": "jpeg", 
    "identifier": "A0CB51BE7EED435A93E23C3BE0886944", 
    "height": 1080, 
    "md5": "e782060a72bc99cb08143e7a70f9b2ca", 
    "focalLength": "(null)",
    "file_path": /kelso/....
    "md5":5969020b22b2350ac9c757ca70fcce26
    """
    n = 0
    for pic in pic_list:
        if pic.has_key('file_path'):
            pic_url,pic_id = upload_pic(pic["file_path"],)
            pic["url"] = pic_url
            pic["id"] = pic_id
            n = n + 1

    print "打印 dayone_photos_list 内容:"
    for x in pic_list:
        print x
    return pic_list,n


def get_thumbnail_img_id(photos_info_list):
    for photos_info in photos_info_list:
        if photos_info["orderInEntry"] == 0:
            return photos_info["id"]

def deal_content_raw(content_raw,photos_info_list):
    # ![](dayone-moment://A0CB51BE7EED435A93E23C3BE0886944)

    if len(photos_info_list)>0:
        for photos_info in photos_info_list:
            # print "照片标识符", photos_info["identifier"]
            # print "照片path", photos_info["file_path"]
            # print "照片url", photos_info["url"]
            if photos_info["url"]:
                content_raw = content_raw.replace("dayone-moment://"+photos_info["identifier"],photos_info["url"])
    return content_raw


def upload_post(post_title,post_content,img_id = "",post_date = "",post_format = "standard",post_status = "publish",post_tag = ""):
    post = WordPressPost()
    #标题
    post.title = post_title
    # 内容
    post.content = post_content


    # 时间
    if post_date != "" :
        post.date = post_date

    #tag
    if post_tag:
        post.terms_names = {
            'post_tag': post_tag,
            }


    # 格式,默认为standard
    post.post_format = post_format

    post.post_status = post_status
    post.comment_status = "open"

    #设置为特色图像
    if (len(img_id)>0):
        post.thumbnail = img_id
    post.id = client.call(posts.NewPost(post))


    return post.id

def notification(title,content):
    command = "osascript -e \'display notification \"%s\" with title \"%s\"\'"%(content,title)
    os.system(command)

def deal_meta_end(post_id,meta_data = []):
    if len(meta_data) > 0:
        meta_data.insert(0,post_id)
        print "发表成功,准备打印数据"
        post_id_int = str(meta_data)
    else:
        post_id_int = filter(str.isdigit, post_id.encode("utf-8"))
        #复制到粘贴板

    print "DONE! 数据已复制到粘贴板,请手动粘贴到脚注中>>"
    os.system("echo '%s' | pbcopy" % post_id_int)

def old_post_with_pic(post_id,photos_info_list,content_raw,post_date):

    print "取得wp中的配图信息-------------------------------"
    wp_img_info = get_wp_post_img(post_id)
    #wp_img_info结构:[{"id":1234,"img_url":"http://...jpg"},...]
    if wp_img_info:
        print "共找着%s张插图"%len(wp_img_info)
        print "删除全部旧文章配图"
        del_post_img_out(wp_img_info)

    print "取得本地配图-----------------------------"

    print "处理photo,添加本地路径"
    photos_info_list = add_photos_path(photos_info_list)

    print "上传本地photo,写入key"
    photos_info_list,n = upload_pic_list(photos_info_list)
    print "共上传了%s张图片"%n
    #得到特色图片id
    thumbnail_img_id = get_thumbnail_img_id(photos_info_list)

    print "分离标题与内容"
    post_title = content_raw[0:content_raw.find('\n')]
    post_content = content_raw[content_raw.find('\n') + 1:]

    while post_title[0] == "#":
    #去掉#号
        post_title = post_title[1:]

    while post_content[0] == "\n":
    #去掉首行空行
        post_content = post_content[1:]

    while ("![](dayone-moment" in post_title) or (post_title == "\n"):
        print "标题有问题"
        first_img = post_title
        post_title = post_content[0:post_content.find('\n')]
        print "new title:",post_title

        post_content = first_img +"\n"+ post_content[post_content.find('\n') + 2:]

    # print "title:", post_title
    # print "content:",post_content
    

    print "替换里的图片地址为url"
    post_content_markdown = deal_content_raw(post_content,photos_info_list)


    print "转md to html"
    post_content = mistune.markdown(post_content_markdown.encode("utf-8"))
    # print post_content
    global music_url
    global wp_post_tag
    if music_url:
        post_content =add_music(post_content,music_url)
        wp_post_tag.append("音乐")
    

    print "修改wp文章"
    edit_dlmao_post(post_title,post_content,post_id,img_id =thumbnail_img_id,post_status = post_status,post_date = post_date,post_tag = wp_post_tag,post_format = post_format)
    print "完成"



    return post_id, n

def old_post_without_pic(post_id,content_raw,post_date):
    print "新的文章没有配图"

    print "处理标题"
    post_title = content_raw[0:content_raw.find('\n')]
    while post_title[0] == "#":
        post_title = post_title[1:]

    print "处理内容"
    post_content = content_raw[content_raw.find('\n') + 1:]

    print "转md to html"
    post_content = mistune.markdown(post_content.encode("utf-8"))

    global music_url
    global wp_post_tag
    if music_url:
        post_content =add_music(post_content,music_url)
        wp_post_tag.append("音乐")
    
    # print "文章内容:"
    # print post_content
    print "修改wp文章"
    edit_dlmao_post(post_title,post_content,post_id,post_status = post_status,post_date = post_date,post_tag = wp_post_tag,post_format = post_format)
    print "完成"
    
    print "删除wp未附加的图片"
    wp_post_img_list = get_wp_post_img(post_id)
    del_post_img_out(wp_post_img_list)


def del_post_img_out(wp_img_list):
    if len(wp_img_list)>0:
        #删除云端wp多余的图
        for del_img in wp_img_list:
            client.call(posts.DeletePost(del_img['id']))

        print "删除云端wp多余的图片共%s张"%len(wp_img_list)
    else:
        print "没有删除任何wp图片"

def get_wp_post_img(post_id):
    img_list = []
    post_img_list = client.call(media.GetMediaLibrary({"parent_id":post_id}))
    if len(post_img_list)>0:
        for img in post_img_list:
            # id
            # parent
            # title
            # description
            # caption
            # date_created (datetime)
            # link
            # thumbnail
            # metadata
            img_list.append({"id":img.id,"img_url":img.link})

    return img_list

def open_link_in_browser(post_id):
    post_link = "https://dlmao.com/"+post_id
    import webbrowser
    webbrowser.open_new(post_link)
    return post_link

def get_post_tag(entries):
    post_id = False
    music_url = False
    post_status = "publish"
    post_format = "standard"
    global wp_post_tag
    Preset_tag = ["音乐","随手拍","设计","视频","电影","生日","游戏","旅行","教程","推荐","技巧","吉他","代码","败家"]
    if entries.has_key('tags'):
        for tag in entries["tags"]:
            # print "tag:", tag
            if tag[-4:] == ".mp3" or tag[-4:] == ".m4a":
                music_url = tag
            elif tag.startswith("postid"):
                post_id = tag[7:]
            elif len(filter(str.isdigit, tag.encode("utf-8"))) == 4:
                post_id = filter(str.isdigit, tag.encode("utf-8"))
            elif tag == "private" or tag == "p":
                post_status = "private"
            elif tag == "image" or tag == "postformat:image":
                post_format = "image"
            elif tag in Preset_tag:
                wp_post_tag.append(tag)

    return post_id,music_url,post_status,post_format

def edit_dlmao_post(new_post_title,new_post_content,post_id,img_id = "",post_date = "",post_format = "standard",post_status = "publish",post_tag = ""):

    old_post = WordPressPost()
    old_post.title = new_post_title
    old_post.content = new_post_content

    # 时间
    if post_date != "" :
        old_post.date = post_date

    #tag
    if len(post_tag)>0:
        old_post.terms_names = {
            'post_tag': post_tag,
            }
    #设置为特色图像
    if (len(img_id)>0):
        old_post.thumbnail = img_id
    

    old_post.post_format = post_format
    old_post.post_status = post_status
    old_post.comment_status = "open"

    client.call(posts.EditPost(post_id,old_post))

def new_post_without_pic(content_raw,post_date):

    print "处理标题"
    post_title = content_raw[0:content_raw.find('\n')]
    while post_title[0] == "#":
        post_title = post_title[1:]

    print "处理内容"
    post_content_markdown = content_raw[content_raw.find('\n') + 1:]
    print "转md to html"
    post_content = mistune.markdown(post_content_markdown.encode("utf-8"))

    global music_url
    global wp_post_tag
    if music_url:
        post_content =add_music(post_content,music_url)
        wp_post_tag.append("音乐")
    

    print "上传文章"
    post_id = upload_post(post_title,post_content,post_status = post_status,post_date = post_date,post_tag = wp_post_tag,post_format = post_format)

    print "上传成功,post id:",post_id
    return post_id

def add_music(content,url):
    music_script = "[audio loop=\"false\" src=\"%s\"]"%url
    content = content + music_script
    return content



#输入wordpress，并创建为一个实例
client = Client('https://your_url.com/xmlrpc.php', 'wordpress_user', 'wordpress_password')
json_path = 'NONE'

for f in sys.argv[1:]:
    if os.path.isfile(f):
        json_path = f

print "连接数据完毕"

if os.path.exists(json_path):
    print "初始化本地数据------------------------------------------------------------------------------"
    with open( json_path , 'r') as f:
        data = json.load(f)
    #data 为一个字典,所有有用的信息都在entries里,entries为一个list
    wp_post_tag = []
    entries = data["entries"][0]
    content_raw = entries["text"]

    creationDate =entries["creationDate"]
    post_date = datetime.datetime.strptime(creationDate, "%Y-%m-%dT%H:%M:%SZ")

    photos_info_list = dayone_have_pic(json_path,entries)
    post_id,music_url,post_status,post_format = get_post_tag(entries)
    print "本地数据初化完毕------------------------------------------------------------------------------"
    notification("本地数据初化完毕！",json_path)
    if post_id:
        # 旧文章流程------------------------------------------------------------------------------
        print "旧文章，posdid为:",post_id
        if photos_info_list:
            postid,num_photo = old_post_with_pic(post_id,photos_info_list,content_raw,post_date)
            if num_photo > 0:
                notification("旧文章更新成功","此次共上传图片%s张"%num_photo)
            else:
                notification("旧文章更新成功","图片未作修改")
        else:
            old_post_without_pic(post_id,content_raw,post_date)
            notification("旧文章更新成功","未上传任何图片")
    else:
        # 新文章流程------------------------------------------------------------------------------
        print "新文章"
        if photos_info_list:
            post_id,num_photo = new_post_with_pic(content_raw,photos_info_list,post_date)
            notification("文章发表成功","请粘贴post_id到标签,此次共上传图片%s张"%num_photo)
        else:
            post_id = new_post_without_pic(content_raw,post_date)
            notification("文章发表成功","请粘贴post_id到标签,没有配图")

    deal_meta_end(post_id)
    open_link_in_browser(post_id)
else:
    notification("参数传入错误","请从dayone中打开此程序")



