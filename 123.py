import re

a = "oloro che vogliono comprare un telefono per tenerlo il più a lungo possibile. Un processore "\
"tanto potente, porta ad un rammarico ancora più grande per le dimensioni minuscole dello schermo; iPhone SE 3 grazie al "\
"suo processore potrebbe fare molto di più se solo avesse uno schermo più grande. La componente fotografica è un elemento fondamentale "\
"di uno smartphone e quando si scorrono le specifiche di iPhone SE 3 si corre il rischio di restare delusi. Sulla carta sarebbe "\
"un iPhone 8, quindi un telefono del 2017: lente singola, 12 megapixel, apertura ƒ/1.8. Niente super grandangolo e "\
"niente zoom. Ma come spiega Apple, quando si parla di fotografia riferendosi ad un iPhone si deve parlare del "\
"sistema e non della componente e il sistema di iPhone SE permette di avere risultati di buon "\
"livello. <span data-mce-type=”bookmark” style=”display: inline-block; width: 0px; overflow: hidden; line-height: 0;” class=”mce_SELRES_start”> Qui "\
"sopra il confronto con iPhone 13 Pro. Si nota ha una gamma cromatica più precisa, interpreta la tinta "\
"degli oggetti in maniera più puntale (notate il colore dei chicchi o del limone) ma anche quelli di iPhone 12 "\
"Pro sono saturi e realistici, il bilanciamento del bianco produce immagini piacevoli e c’è anche una certa ricchezza "\
"di dettaglio. Il merito è sicuramente del processore immagine di A15 che introduce funzioni "\
"come Deep Fusion e Smart HDR4. Ci sono anche gli stili fotografici che permettono di aggiungere un tocco di "\
"creatività e persino la funzione ritratto. <span data-mce-type=”bookmark” style=”display: inline-block; width: 0px; overflow: hidden; line-height: 0;” class=”mce_SELRES_start”> Il risu"

b = re.sub(r'<span[\w\d\s\”\=\_\-\:\’\/\;]+”>|\</span\>', '', a).strip()

# print(a)
print(b)