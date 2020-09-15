import re
import scrapy   
from time import sleep
from functools import partial

from scrapy.crawler import CrawlerProcess

DOMAIN_REG = r'm-est\.ru'
DOMAIN = 'http://m-est.ru'


"""
на выходе мне нужен словарь
d = { 'base_url' : '' - откуда ссылка
      'url': '' - куда ведет
      'text': '' - текст в анкоре
"""

def is_inner_link(url):
    url = url.lower()
    reg =  r'^(?:/)|(?:\./)|(?:https?://www\.'+ DOMAIN_REG + '/)|(?:https?://'+ DOMAIN_REG + '/)'
    return True if re.match(reg, url) else False

def is_outer_link(url):
    reg = r'(?:https?://)'
    return True if re.match(reg, url) and not is_inner_link(url) else False

def correct_links(link, base_url=''):
    """
    выкидывает невалидные ссылки. ссылки вида index.php (без /)
    заменяет на ./index.php, отрубает часть с # и тд
    """
    link = link.split('#')[0]

    if re.match(r'^\w+\.(?:(?:html)|(?:php)){1}', link):
        base = '/'.join(base_url.split('/')[:-1])
        link = base + '/' + link
    return link


outer_links = []
parsed_urls = []

class LinkSpider(scrapy.Spider):
    name = "LinkSpider"
    
    def __init__(self):
        self.visited_links = []
    
    def start_requests(self):
        urls = [DOMAIN]
        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)
            
    def parse(self, response):
        links = response.xpath('//a/@href').extract()
        texts = response.xpath('//a/text()').extract()
        current_url = response.request.url
        
        parsed_urls.append(current_url)
      
        # есть тонкость - иногда ссылки идут в виде <a href='index.html'> 
        # и нужно руками добавлять базу, иногда они содержат не нужный нам символ #
        correct_filter = partial(correct_links, base_url=current_url)
        links = map(correct_filter, links)

        # возможные появившиеся пустышки отсеятся сами - не попадут ни под какой из 2 типов
        links_to_crowl = []
        for link, text in zip(links, texts):
            if is_outer_link(link):
                outer_links.append({'base_url':current_url, 'url':link, 'text':text})
            elif is_inner_link(link) and (link.endswith('.php') or link.endswith('.html') or link.endswith('/')):
                links_to_crowl.append(link)
                
        for link in links_to_crowl:
            if link.startswith('/'):
                link = DOMAIN + link            
            if not link in self.visited_links:
                self.visited_links.append(link)                    
                parsed_urls.append(link)
                yield scrapy.Request(url=link, callback=self.parse)

process = scrapy.crawler.CrawlerProcess()
process.crawl(LinkSpider)
process.start()

string = "Внешние ссылки:\n\n"
for item in outer_links:
    string += "\n{} : {} : {}".format(item['base_url'], item['url'], item['text'])

with open('links.txt', 'w') as fp:
    fp.write(string)

string = "Просмотренные страницы\n\n"
for link in set(parsed_urls):
    string += "\n{}".format(link)
    
with open('parsed.txt', 'w') as fp:
    fp.write(string)
    