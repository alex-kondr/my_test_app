import json

a='''(function() {
    window.controllerConfigHead = {"minDiskCost":1000,"maxDiskCost":100000,"minTyreCost":1000,"maxTyreCost":100000,"minSpecCost":1000,"maxSpecCost":2000000,"allOpinionsLink":"\/opinions\/search?count=0&modelSlug=formula-energy-12630351&goProducer=102462","tire-service.url":"https:\/\/api-partner.4tochki.ru","tire-service.frontend":"https:\/\/partner.4tochki.ru\/","metricaId":"36434"};
    window.controllerConfigHead.get = function(key, defvalue) {
        if (window.controllerConfigHead.hasOwnProperty(key)) {
            return window.controllerConfigHead[key];
        }
        return defvalue;        
    };
})();'''
b = a.split('window.controllerConfigHead = ')[-1].split('};', 1)[0] + '}'
c = json.loads(b)
print(c)