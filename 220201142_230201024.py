import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
    QWidget, QPushButton, QTextEdit, QLabel, QGraphicsView, QGraphicsScene, 
    QGraphicsEllipseItem, QGraphicsLineItem, QMessageBox,
    QInputDialog, QScrollArea, QDialog, QSpacerItem, QSizePolicy
)
from PyQt5.QtGui import QPen, QColor, QBrush, QFont
from PyQt5.QtCore import Qt, QTimer
import pandas as pd
import random
from pyvis.network import Network
from collections import defaultdict
import ast

class Yazar:
    def __init__(self, orcid, name):
        self.orcid = orcid
        self.name = name
        self.papers = []
        self.connections = []

    def __repr__(self):
        return f"Yazar({self.name}, {self.orcid})"

class Makale:
    def __init__(self, doi, title):
        self.doi = doi
        self.title = title
        self.authors = []

    def __repr__(self):
        return f"Makale({self.title}, {self.doi})"

class Graf:
    def __init__(self):
        self.nodes = []

    def dugum_ekle(self, yazar):
        if yazar not in self.nodes:
            self.nodes.append(yazar)

    def kenar_ekle(self, yazar1, yazar2, ortak_makale_sayisi):
        if yazar2 not in [conn[0] for conn in yazar1.connections]:
            yazar1.connections.append((yazar2, ortak_makale_sayisi))
        if yazar1 not in [conn[0] for conn in yazar2.connections]:
            yazar2.connections.append((yazar1, ortak_makale_sayisi))

    def tum_yollar_bul(self, yazar_a, yazar_b, yol=[], toplam_agirlik=0): #R
        yol = yol + [yazar_a]
        if yazar_a == yazar_b:
            return [(yol, toplam_agirlik)]
        if yazar_a not in self.nodes:
            return []
        tum_yollar = []
        for komsu, agirlik in yazar_a.connections:
            if komsu not in yol:
                yeni_yollar = self.tum_yollar_bul(komsu, yazar_b, yol, toplam_agirlik + agirlik)
                for yeni_yol in yeni_yollar:
                    tum_yollar.append(yeni_yol)
        return tum_yollar

    def en_kisa_yol_bul(self, tum_yollar): #R
        return min(tum_yollar, key=lambda x: x[1]) if tum_yollar else None
    
    def en_kisa_yollar_hesapla(self, yazar):
        en_kısa_yollar = {}
        for diger_yazar in self.nodes:
            if diger_yazar != yazar:
                tum_yollar = self.tum_yollar_bul(yazar, diger_yazar)
                en_kısa_YOL = self.en_kisa_yol_bul(tum_yollar)
                if en_kısa_YOL:
                    en_kısa_yollar[diger_yazar.orcid] = en_kısa_YOL
        return en_kısa_yollar
    
    def kuyruktan_bst_olustur(self, queue):
        class TreeNode:
            def __init__(self, author):
                self.author = author
                self.left = None
                self.right = None

        def ekle(root, author):
            if root is None:
                return TreeNode(author)
            if len(author.papers) < len(root.author.papers):
                root.left = ekle(root.left, author)
            else:
                root.right = ekle(root.right, author)
            return root

        bst_root = None
        for coauthor, _ in queue:
            bst_root = ekle(bst_root, coauthor)
        return bst_root

    def ortak_yazar_sayisi_hesapla(self, yazar):
        return len(yazar.connections)

    def en_cok_isbirligi_yapan_yazari_bul(self):
        if not self.nodes:
            return None, 0
        en_cok_isbirligi_yapan_yazar = max(self.nodes, key=lambda a: len(a.connections), default=None)
        toplam_isbirligi = len(en_cok_isbirligi_yapan_yazar.connections) if en_cok_isbirligi_yapan_yazar else 0
        return en_cok_isbirligi_yapan_yazar, toplam_isbirligi

    def en_uzun_yol_bul(self, yazar_id):
        en_uzun_yol = []
        ziyaret_edildi = set()
        yigin = []
        author = next((a for a in self.nodes if a.orcid == yazar_id), None)
        if not author:
            print("Hata: Verilen ID'ye sahip bir yazar bulunamadı.")
            return []
        yigin.append((author, [author]))
        while yigin:
            simdiki_author, path = yigin.pop()
            ziyaret_edildi.add(simdiki_author)
            if len(path) > len(en_uzun_yol):
                en_uzun_yol = path.copy()
            for komsu, _ in simdiki_author.connections:
                if komsu not in ziyaret_edildi and komsu not in path:
                    new_path = path + [komsu]
                    yigin.append((komsu, new_path))
        return en_uzun_yol

dosya = "PROLAB 3 - GÜNCEL DATASET.xlsx"
veriseti = pd.read_excel(dosya)

yazarlar = {}
makaleler = {}
yazar_ismi_haritası = defaultdict(list)
orcid_sayaci = 1

graf = Graf()

for _, row in veriseti.iterrows():
    orcid = row['orcid']
    author_name = row['author_name']
    
    if orcid not in yazarlar:
        yeni_yazar = Yazar(orcid, author_name)
        yazarlar[orcid] = yeni_yazar
        yazar_ismi_haritası[author_name].append(yeni_yazar)
    else:
        existing_author = yazarlar[orcid]
        if existing_author.name != author_name:
            yeni_yazar = Yazar(orcid, author_name)
            yazar_ismi_haritası[author_name].append(yeni_yazar)

for _, row in veriseti.iterrows():
    orcid = row['orcid']
    doi = row['doi']
    paper_title = row['paper_title']
    author_position = row['author_position']

    try:
        coauthors = ast.literal_eval(row['coauthors']) if isinstance(row['coauthors'], str) else []
        if not isinstance(coauthors, list):
            raise ValueError("Coauthors sütunu geçerli bir liste değil.")
    except Exception as e:
        print(f"Hata: DOI {doi} için coauthors ayrıştırma hatası: {e}")
        coauthors = []
    
    merkez_yazar = yazarlar.get(orcid)

    if doi not in makaleler:
        makaleler[doi] = Makale(doi, paper_title)

    yazar = yazarlar[orcid]
    if makaleler[doi] not in yazar.papers:
        yazar.papers.append(makaleler[doi])
    if yazar not in makaleler[doi].authors:
        makaleler[doi].authors.append(yazar)

    author_name_in_position = coauthors[author_position - 1] if 0 < author_position <= len(coauthors) else None

    if author_name_in_position:
        coauthors.remove(author_name_in_position)
        for coauthor_name in coauthors:
            found_author = None
            for existing_author in yazar_ismi_haritası.get(coauthor_name, []):
                if existing_author.orcid == orcid:
                    found_author = existing_author
                    break

            if found_author is None:
                if coauthor_name in yazar_ismi_haritası:
                    found_author = yazar_ismi_haritası[coauthor_name][0]
                else:
                    new_orcid = f"ORCID{orcid_sayaci:05d}"
                    orcid_sayaci += 1
                    found_author = Yazar(new_orcid, coauthor_name)
                    yazarlar[new_orcid] = found_author
                    yazar_ismi_haritası[coauthor_name].append(found_author)

            if makaleler[doi] not in found_author.papers:
                found_author.papers.append(makaleler[doi])
            if found_author not in makaleler[doi].authors:
                makaleler[doi].authors.append(found_author)

for _, row in veriseti.iterrows():
    orcid = row['orcid']
    author_name = row['author_name']
    doi = row['doi']
    paper_title = row['paper_title']
    author_position = row['author_position']
    try:
        coauthors = ast.literal_eval(row['coauthors']) if isinstance(row['coauthors'], str) else []
        if not isinstance(coauthors, list):
            raise ValueError("Coauthors sutunu gecerli bir liste degil.")
    except Exception as e:
        print(f"Hata: DOI {doi} icin coauthors ayristirma hatasi: {e}")
        coauthors = []
        
    merkez_yazar = yazarlar.get(orcid)

    for coauthor_name in coauthors:
        if coauthor_name in yazar_ismi_haritası:
            coauthor = yazar_ismi_haritası[coauthor_name][0]
            if coauthor != merkez_yazar:
                ortak_makale_sayisi = len(set([makale.doi for makale in merkez_yazar.papers]).intersection(set([makale.doi for makale in coauthor.papers])))

                if ortak_makale_sayisi > 0:
                    graf.kenar_ekle(merkez_yazar, coauthor, ortak_makale_sayisi)

for yazar in yazarlar.values():
    graf.dugum_ekle(yazar)


class TiklanabilirElips(QGraphicsEllipseItem):
    def __init__(self, x, y, radius, author, *args, **kwargs):
        super().__init__(x, y, radius, radius, *args, **kwargs)
        self.author = author

    def mousePressEvent(self, event):
        print(f"Tıklanan yazar: {self.author.name}, ORCID: {self.author.orcid}")
        try:
            dialog = QDialog()
            dialog.setWindowTitle("Yazar Bilgisi")
            dialog.setMinimumSize(400, 300)
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            content_widget = QWidget()
            content_layout = QVBoxLayout(content_widget)
            papers_list = "\n".join([paper.title for paper in self.author.papers])
            message = f"Yazar: {self.author.name}\nORCID: {self.author.orcid}\nMakaleler:\n{papers_list}"
            content_layout.addWidget(QLabel(message))
            content_widget.setLayout(content_layout)
            scroll_area.setWidget(content_widget)
            dialog_layout = QVBoxLayout(dialog)
            dialog_layout.addWidget(scroll_area)
            dialog.setLayout(dialog_layout)
            dialog.exec_()
        except Exception as e:
            QMessageBox.critical(None, "Hata", f"Bir hata oluştu: {str(e)}")

class TiklanabilirCizgi(QGraphicsLineItem):
    def __init__(self, start_author, end_author, ortak_makale_sayisi, start_x, start_y, end_x, end_y, *args, **kwargs):
        super().__init__(start_x, start_y, end_x, end_y, *args, **kwargs)
        self.start_author = start_author
        self.end_author = end_author
        self.ortak_makale_sayisi = ortak_makale_sayisi

    def mousePressEvent(self, event):
        QMessageBox.information(None, "Ortak Makale Sayisi", 
                                f"{self.start_author.name} ve {self.end_author.name} arasında ortak makale sayısı: {self.ortak_makale_sayisi}")
        super().mousePressEvent(event)

class GrafArayuzu(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Graf İşemleri")
        self.setGeometry(100, 100, 2400, 1200)
        self.setMinimumSize(1600, 900)
        container = QWidget()
        self.setCentralWidget(container)
        main_layout = QHBoxLayout()
        left_layout = QVBoxLayout()
        center_layout = QVBoxLayout()
        right_layout = QVBoxLayout()
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        left_layout.addWidget(QLabel("ÇIKTI EKRANI"))
        left_layout.addWidget(self.output_area)
        self.graph_view = QGraphicsView()
        self.scene = QGraphicsScene()
        self.graph_view.setScene(self.scene)
        self.graph_view.setMinimumSize(1600, 800)
        center_layout.addWidget(QLabel("GRAF GÖRSELİ"))
        center_layout.addWidget(self.graph_view)
        right_layout.addWidget(QLabel("İŞLEMLER"))
        right_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        self.buttons = []
        button_labels = [
            "1. İSTER",
            "2. İSTER",
            "3. İSTER",
            "4. İSTER",
            "5. İSTER",
            "6. İSTER",
            "7. İSTER"
        ]
        for label in button_labels:
            button = QPushButton(label)
            button.setFixedSize(150, 50)
            button.setStyleSheet("background-color: lightblue; font-size: 16px;")
            button.clicked.connect(self.buton_tiklandi)
            self.buttons.append(button)
            right_layout.addWidget(button)
        right_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        main_layout.addLayout(left_layout, 2)
        main_layout.addLayout(center_layout, 3)
        main_layout.addLayout(right_layout, 1)
        container.setLayout(main_layout)

        self.node_positions = {}
        self.grafi_ciz()
        self.shortest_path_1 = None
        self.shortest_path_4 = None
        self.node_positions = {} 

    def grafi_sifirla(self, reset_shortest_path=True):
        if reset_shortest_path:
            self.shortest_path_1 = None
            self.shortest_path_4 = None
        self.longest_path = None
        self.grafi_ciz()

    def bst_ciz(self, root):
        if root is None:
            return
        self.bst_ciz(root.left)
        print(f"Dugum: {root.author.name}, ORCID: {root.author.orcid}")
        self.bst_ciz(root.right)

    def al_en_kucuk(self, node):
        current = node
        while current.left is not None:
            current = current.left
        return current

    def bstden_dugum_sil(self, root, author):
        if root is None:
            print("Dugum bulunamadi.")
            return root

        if len(author.papers) < len(root.author.papers):
            print(f"Sol alt ağaçta aranıyor: {root.author.name} (Makaleler: {len(root.author.papers)})")
            root.left = self.bstden_dugum_sil(root.left, author)
        elif len(author.papers) > len(root.author.papers):
            print(f"Sağ alt ağaçta aranıyor: {root.author.name} (Makaleler: {len(root.author.papers)})")
            root.right = self.bstden_dugum_sil(root.right, author)
        else:
            if author.orcid == root.author.orcid:
                print(f"DÜğüm siliniyor: {root.author.name} (Makaleler: {len(root.author.papers)})")
                
                if root.left is None:
                    return root.right
                elif root.right is None:
                    return root.left

                min_larger_node = self.al_en_kucuk(root.right)
                root.author = min_larger_node.author
                root.right = self.bstden_dugum_sil(root.right, min_larger_node.author)

            else:
                print(f"Uygun düğüm bulunamadı: {root.author.name} (Makaleler: {len(root.author.papers)})")
                root.left = self.bstden_dugum_sil(root.left, author)
                root.right = self.bstden_dugum_sil(root.right, author)

        return root

    def grafi_ciz(self):
        self.scene.clear()
        positions = self.node_positions 
        toplam_makale_sayisi = sum(len(yazar.papers) for yazar in graf.nodes)
        toplam_yazar_sayisi = len(graf.nodes)
        ortalama_makale_sayisi = toplam_makale_sayisi / toplam_yazar_sayisi if toplam_yazar_sayisi > 0 else 0
        max_makale_sayisi = max(len(yazar.papers) for yazar in graf.nodes)

        for i, yazar in enumerate(graf.nodes):
            yazar_makale_sayisi = len(yazar.papers)
            alpha = int(255 * (1 - (yazar_makale_sayisi / max_makale_sayisi)))
            alpha = max(alpha, 0)
            if yazar_makale_sayisi > ortalama_makale_sayisi * 1.2:
                radius = 20 + (yazar_makale_sayisi / ortalama_makale_sayisi) * 30
                color = QColor(173, 216, 230, alpha)
            elif yazar_makale_sayisi < ortalama_makale_sayisi * 0.8:
                radius = 20 + (yazar_makale_sayisi / max_makale_sayisi) * 10
                color = QColor(0, 191, 255, alpha)
            else:
                color = QColor(135, 206, 250, alpha)
            if yazar in positions:
                x, y, radius = positions[yazar]
            else:
                x = random.randint(50, 1550)
                y = random.randint(50, 750)
                radius = 20 + (yazar_makale_sayisi / max_makale_sayisi) * 20
                positions[yazar] = (x, y, radius) 

            ellipse_item = TiklanabilirElips(x, y, radius, yazar)
            brush = QBrush(color)
            renk = QColor(200, 200, 200, 150)
            if hasattr(self, 'shortest_path_1') and self.shortest_path_1 is not None and yazar in self.shortest_path_1:
                renk = QColor(255, 0, 0)
            if hasattr(self, 'longest_path') and self.longest_path is not None and yazar in self.longest_path:
                renk = QColor(255, 0, 0)
            pen = QPen(renk)
            ellipse_item.setBrush(brush)
            ellipse_item.setPen(QPen(renk))
            self.scene.addItem(ellipse_item)
            text_item = self.scene.addText(yazar.name)
            text_item.setFont(QFont("Arial", 1))
            text_item.setDefaultTextColor(QColor(80, 80, 80))
            text_item.setPos(x, y - (radius / 2))

        drawn_edges = set()
        for yazar in graf.nodes:
            start_x, start_y, radius = positions[yazar]
            center_x = start_x + radius / 2
            center_y = start_y + radius / 2
            for neighbor, _ in yazar.connections:
                if neighbor in positions:
                    end_x, end_y, neighbor_radius = positions[neighbor]
                    neighbor_center_x = end_x + neighbor_radius / 2
                    neighbor_center_y = end_y + neighbor_radius / 2
                    edge = (yazar, neighbor)
                    if edge not in drawn_edges:
                        line = self.scene.addLine(center_x, center_y, 
                                                  neighbor_center_x, neighbor_center_y, 
                                                   QColor(200, 200, 200, 150))
                        line.setPen(QPen(QColor(200, 200, 200, 150), 0.3, Qt.SolidLine))
                        drawn_edges.add(edge)
        for yazar in graf.nodes:
            print(f"{yazar.name}: {[neighbor[0].name for neighbor in yazar.connections]}")
        if hasattr(self, 'shortest_path_1') and self.shortest_path_1 is not None:
            for i in range(len(self.shortest_path_1) - 1):
                start_author = self.shortest_path_1[i]
                end_author = self.shortest_path_1[i + 1]
                start_x, start_y, radius = positions[start_author]
                end_x, end_y, neighbor_radius = positions[end_author]
                center_x = start_x + radius / 2
                center_y = start_y + radius / 2
                neighbor_center_x = end_x + neighbor_radius / 2
                neighbor_center_y = end_y + neighbor_radius / 2
                line = self.scene.addLine(center_x, center_y, 
                                          neighbor_center_x, neighbor_center_y, 
                                          QColor(255, 0, 0, 150))
                line.setPen(QPen(QColor(255, 0, 0, 150), 0.3, Qt.SolidLine))
        if hasattr(self, 'longest_path') and self.longest_path is not None:
            for i in range(len(self.longest_path) - 1):
                start_author = self.longest_path[i]
                end_author = self.longest_path[i + 1]
                start_x, start_y, radius = positions[start_author]
                end_x, end_y, neighbor_radius = positions[end_author]
                center_x = start_x + radius / 2
                center_y = start_y + radius / 2
                neighbor_center_x = end_x + neighbor_radius / 2
                neighbor_center_y = end_y + neighbor_radius / 2
                line = self.scene.addLine(center_x, center_y, 
                                          neighbor_center_x, neighbor_center_y, 
                                          QColor(255, 0, 0, 150))
                line.setPen(QPen(QColor(255, 0, 0, 150), 0.3, Qt.SolidLine))

    def en_kisa_yol_agacini_ciz(self, bst_root):
        self.scene.clear()
        positions = {}

        def dugum_ekle(node, x, y, dx):
            if node is not None:
                yazar_makale_sayisi = len(node.author.papers) 
                tomlam_makale_sayisi = sum(len(author.papers) for author in graf.nodes)
                toplam_yazar_sayisi = len(graf.nodes)
                ortalama_makale_sayisi = tomlam_makale_sayisi  / toplam_yazar_sayisi if toplam_yazar_sayisi > 0 else 0
                max_makale_sayisi = max(len(author.papers) for author in graf.nodes)

                alpha = int(255 * (1 - (yazar_makale_sayisi / max_makale_sayisi)))
                alpha = max(alpha, 0)

                if yazar_makale_sayisi > ortalama_makale_sayisi * 1.2:
                    radius = 20 + (yazar_makale_sayisi / max_makale_sayisi) * 30
                    color = QColor(173, 216, 230, alpha)
                elif yazar_makale_sayisi < ortalama_makale_sayisi * 0.8:
                    radius = 20 + (yazar_makale_sayisi / max_makale_sayisi) * 10
                    color = QColor(0, 191, 255, alpha)
                else:
                    radius = 20 + (yazar_makale_sayisi / max_makale_sayisi) * 20
                    color = QColor(135, 206, 250, alpha)

                ellipse_item = TiklanabilirElips(x, y, radius, node.author)
                ellipse_item.setBrush(QBrush(color))
                self.scene.addItem(ellipse_item)

                text_item = self.scene.addText(node.author.name)
                text_item.setFont(QFont("Arial", 3)) 
                text_item.setDefaultTextColor(QColor(100, 100, 100))  
                text_item.setPos(x + radius / 2 - text_item.boundingRect().width() / 2, 
                                 y + radius / 2 - text_item.boundingRect().height() / 2)

                positions[node] = (x, y, radius)

                dugum_ekle(node.left, x - dx, y + 50, dx / 2)
                dugum_ekle(node.right, x + dx, y + 50, dx / 2)

        center_x = self.width() / 2
        center_y = self.height() / 2
        dugum_ekle(bst_root, center_x, center_y, 200)

        for node in positions.keys():
            start_x, start_y, radius = positions[node]
            center_x = start_x + radius / 2
            center_y = start_y + radius / 2

            if node.left in positions:
                left_x, left_y, left_radius = positions[node.left]
                left_center_x = left_x + left_radius / 2
                left_center_y = left_y + left_radius / 2
                line = self.scene.addLine(center_x, center_y, left_center_x, left_center_y, QColor(200, 200, 200, 150))
                line.setPen(QPen(QColor(200, 200, 200, 150), 1.5, Qt.SolidLine))

            if node.right in positions:
                right_x, right_y, right_radius = positions[node.right]
                right_center_x = right_x + right_radius / 2
                right_center_y = right_y + right_radius / 2
                line = self.scene.addLine(center_x, center_y, right_center_x, right_center_y, QColor(200, 200, 200, 150))
                line.setPen(QPen(QColor(200, 200, 200, 150), 1.5, Qt.SolidLine))

    def yazar_bilgisi_goster(self, author):
        print(f"Tiklanan yazar: {author.name}, ORCID: {author.orcid}")
        makale_listesi = "\n".join([paper.title for paper in author.papers])
        message = f"Yazar: {author.name}\nORCID: {author.orcid}\nMakaleler:\n{makale_listesi}"
        QMessageBox.information(self, "Yazar Bilgisi", message)

    def wheelEvent(self, event):
        zoom_oran = 1.2
        if event.angleDelta().y() < 0:
            zoom_oran = 1.0 / zoom_oran
        self.graph_view.scale(zoom_oran, zoom_oran)

    def agirlikli_kuyruk_olustur(self, author):
        self.output_area.append(f"\n{author.name} ve işbirliği yapan yazarlar sıraya ekleniyor...\n")
        queue = [(author, len(author.papers))]
        self.output_area.append(f"Yazar eklendi: {author.name}, Makale Sayısı: {len(author.papers)}")
        self.output_area.append("Güncel Kuyruk:")
        self.output_area.append(f"  1. {author.name} (Makale Sayısı: {len(author.papers)})")

        for item in self.scene.items():
            if isinstance(item, TiklanabilirElips) and item.author == author:
                pen = QPen(QColor(255, 0, 0), 2) 
                item.setPen(pen)

        timer = QTimer()
        timer.setInterval(1000)
        index = 0

        def komsulari_ekle():
            nonlocal index
            if index < len(author.connections):
                neighbor, weight = author.connections[index]
                queue.append((neighbor, len(neighbor.papers)))
                self.output_area.append(f"\nYazar eklendi: {neighbor.name}, Makale Sayısı: {len(neighbor.papers)}")
                queue.sort(key=lambda x: x[1], reverse=True)
                self.output_area.append("Güncel Kuyruk:")
                for i, (auth, wt) in enumerate(queue):
                    self.output_area.append(f"  {i + 1}. {auth.name} (Makale Sayısı: {wt})")              
            
                for item in self.scene.items():
                    if isinstance(item, TiklanabilirElips) and item.author == neighbor:
                        pen = QPen(QColor(255, 0, 0), 2)  
                        item.setPen(pen)

                index += 1
            else:
                timer.stop()
                self.output_area.append("Tüm yazarlar sıralandı.")

        timer.timeout.connect(komsulari_ekle)
        timer.start()

    def graf4(self, authors, main_author):
        self.scene.clear()  
        drawn_edges = set()  

        total_papers = sum(len(author.papers) for author in authors)
        total_authors = len(authors)
        average_paper_count = total_papers / total_authors if total_authors > 0 else 0
        max_paper_count = max(len(author.papers) for author in authors) if authors else 0

        positions = {author: self.node_positions[author] for author in authors if author in self.node_positions}

        for author in authors:
            if author in positions:
                x, y, radius = positions[author]
                paper_count = len(author.papers)
                alpha = int(255 * (1 - (paper_count / max_paper_count))) if max_paper_count > 0 else 0
                alpha = max(alpha, 0)

                if paper_count > average_paper_count * 1.2:
                    color = QColor(173, 216, 230, alpha)
                elif paper_count < average_paper_count * 0.8:
                    color = QColor(0, 191, 255, alpha)
                else:
                    color = QColor(135, 206, 250, alpha)  

                ellipse_item = TiklanabilirElips(x, y, radius, author)
                ellipse_item.setBrush(QBrush(color))
                ellipse_item.setPen(QPen(QColor(0, 0, 0), 1))  
                self.scene.addItem(ellipse_item)

                text_item = self.scene.addText(author.name)
                text_item.setFont(QFont("Arial", 3))
                text_item.setDefaultTextColor(QColor(100, 100, 100))
                text_item.setPos(x + radius / 2 - text_item.boundingRect().width() / 2, y + radius / 2 - text_item.boundingRect().height() / 2)

                ellipse_item.mousePressEvent = lambda event, a=author: self.yazar_bilgisi_goster(a)

        for author in authors:
            for coauthor, ortak_makale_sayisi in author.connections:
                if coauthor in authors and (author, coauthor) not in drawn_edges:
                    if author in positions and coauthor in positions:
                        start_x, start_y, radius = positions[author]
                        end_x, end_y, _ = positions[coauthor]
                        
                        start_center_x = start_x + radius / 2  
                        start_center_y = start_y + radius / 2  
                        end_center_x = end_x + radius / 2      
                        end_center_y = end_y + radius / 2      
                        
                        line = TiklanabilirCizgi(author, coauthor, ortak_makale_sayisi, start_center_x, start_center_y, end_center_x, end_center_y)
                        line.setPen(QPen(QColor(200, 200, 200, 150), 0.3, Qt.SolidLine))
                        self.scene.addItem(line)
                        drawn_edges.add((author, coauthor))

        for item in self.scene.items():
            if isinstance(item, TiklanabilirElips) and item.author == main_author:
                item.setPen(QPen(QColor(255, 0, 0), 2)) 

    def buton_tiklandi(self):
        sender = self.sender()
        if sender.text() == "1. İSTER":
            self.grafi_sifirla()
            orcid_a, ok_a = QInputDialog.getText(self, "Yazar ID'si", "Birinci yazarın ORCID ID'sini girin:")
            if ok_a:
                orcid_b, ok_b = QInputDialog.getText(self, "Yazar ID'si", "İkinci yazarın ORCID ID'sini girin:")
                if ok_b:
                    yazar_a = next((yazar for yazar in graf.nodes if yazar.orcid == orcid_a), None)
                    yazar_b = next((yazar for yazar in graf.nodes if yazar.orcid == orcid_b), None)
                    if yazar_a and yazar_b:
                        tum_yollar = graf.tum_yollar_bul(yazar_a, yazar_b)
                        self.output_area.clear()
                        self.output_area.append(f"Tüm yollar ({yazar_a.name} - {yazar_b.name}):")
                        for path, weight in tum_yollar:
                            yol_isimleri = " -> ".join(author.name for author in path)
                            self.output_area.append(f"{yol_isimleri} (Ağırlık: {weight})")
                        en_kisa_yol = graf.en_kisa_yol_bul(tum_yollar)
                        if en_kisa_yol:
                            en_kisa_yol_isimleri = " -> ".join(author.name for author in en_kisa_yol[0])
                            self.output_area.append(f"\nEn kısa yol: {en_kisa_yol_isimleri} (Ağırlık: {en_kisa_yol[1]})")
                            self.shortest_path_1 = en_kisa_yol[0]
                            self.grafi_ciz()
                        else:
                            self.output_area.append("En kısa  yol bulunamadı.")
                    else:
                        self.output_area.append("Geçersiz yazar ID'leri.")
                        
        elif sender.text() == "2. İSTER":
            self.grafi_sifirla()
            orcid_a, ok_a = QInputDialog.getText(self, "Yazar ID'si", "Yazarın ORCID ID'sini girin:")
            if ok_a:
                yazar_a = next((yazar for yazar in graf.nodes if yazar.orcid == orcid_a), None)
                if yazar_a:
                    self.output_area.clear()
                    self.output_area.append(f"{yazar_a.name} ile işbirliği yapan yazarlar (Kuyruk):")
                    self.agirlikli_kuyruk_olustur(yazar_a)
                else:
                    self.output_area.append("Geçersiz yazar ID'si.")

        elif sender.text() == "3. İSTER":
            self.grafi_sifirla(reset_shortest_path=False)
            if self.shortest_path_1 is not None:
                path = self.shortest_path_1
                path_bilgisi = " -> ".join(f"{author.name} (ORCID: {author.orcid})" for author in path)
                self.output_area.clear()
                self.output_area.append(f"En kısa yol: {path_bilgisi}")

                queue = [(author, len(author.papers)) for author in path]
                bst_root = graf.kuyruktan_bst_olustur(queue)
                self.output_area.append("Binary ağaç oluşturuldu. Düğüm silmek için bir ORCID girin:")

                self.en_kisa_yol_agacini_ciz(bst_root)

                while True:
                    silinecek_orcid, ok_remove = QInputDialog.getText(self, "ORCID Sil", "Silmek için bir ORCID girin:")
                    if ok_remove and silinecek_orcid:
                        silinecek_yazar = next((yazar for yazar in path if yazar.orcid == silinecek_orcid), None)
                        if silinecek_yazar:
                            bst_root = self.bstden_dugum_sil(bst_root, silinecek_yazar)
                            self.output_area.append(f"Düğüm {silinecek_yazar.name} ağaçtan silindi.")
                            self.output_area.append("Güncellenmiş ağaç graf görselinde gösterildi.")
                            self.en_kisa_yol_agacini_ciz(bst_root)
                            break
                        else:
                            self.output_area.append(f"{silinecek_orcid} ORCID numarasına sahip bir yazar bulunamadı. Lütfen geçerli bir ORCID girin.")
                    else:
                        self.output_area.append("Silme iptal edildi.")
                        break
            else:
                self.output_area.append("Öncek en kısa yolu bulmalısınız.")

        elif sender.text() == "4. İSTER":
            self.grafi_sifirla()
            orcid_a, ok_a = QInputDialog.getText(self, "Yazar ID'si", "Yazarın ORCID ID'sini girin:")
            if ok_a:
                yazar_a = next((yazar for yazar in graf.nodes if yazar.orcid == orcid_a), None)
                if yazar_a:
                    self.output_area.clear()
                    self.output_area.append(f"{yazar_a.name} için tüm yollar hesaplanıyor...\n")
                    
                    en_kisa_yollar = graf.en_kisa_yollar_hesapla(yazar_a)
                    self.shortest_path_4 = en_kisa_yollar
                    
                    baglantili_tum_yazarlar = set()
                    to_visit = [yazar_a]

                    all_paths = []
                    for author in graf.nodes: 
                        if author != yazar_a:  
                            paths = graf.tum_yollar_bul(yazar_a, author)
                            all_paths.extend(paths)

                    self.output_area.append(f"Tüm yollar {yazar_a.name} için:")
                    for path, weight in all_paths:
                        path_names = " -> ".join(author.name for author in path)
                        self.output_area.append(f"{path_names} (Ağırlık: {weight})")

                    while to_visit:
                        current_author = to_visit.pop()
                        if current_author not in baglantili_tum_yazarlar:
                            baglantili_tum_yazarlar.add(current_author)
                            for coauthor, _ in current_author.connections:
                                if coauthor not in baglantili_tum_yazarlar:
                                    to_visit.append(coauthor)

                    self.graf4(baglantili_tum_yazarlar, yazar_a)

                    if en_kisa_yollar:
                        self.output_area.append(f"\n{yazar_a.name} için en kısa yollar:")
                        for coauthor_orcid, path in en_kisa_yollar.items():
                            coauthor = next((yazar for yazar in graf.nodes if yazar.orcid == coauthor_orcid), None)
                            if coauthor:
                                path_names = " -> ".join(author.name for author in path[0])
                                path_weight = path[1]
                                self.output_area.append(f"{yazar_a.name} ile {coauthor.name} arasındaki en kısa yol: {path_names} (Ağırlık: {path_weight})")
                            else:
                                self.output_area.append(f"{yazar_a.name} için herhangi bir yol bulunamadı.")
                    else:
                        self.output_area.append(f"{orcid_a} ORCID numarasına sahip bir yazar bulunamadı.")
                else:
                    self.output_area.append(f"Butona tiklandi: {sender.text()}")

        elif sender.text() == "5. İSTER":
            self.grafi_sifirla()
            orcid_a, ok_a = QInputDialog.getText(self, "Yazar ID'si", "Yazarın ORCID ID'sini girin:")
            if ok_a:
                yazar_a = next((yazar for yazar in graf.nodes if yazar.orcid == orcid_a), None)
                if yazar_a:
                    coauthor_sayaci = graf.ortak_yazar_sayisi_hesapla(yazar_a)
                    self.output_area.clear()
                    self.output_area.append(f"{yazar_a.name} ile işbirliği yapan toplam yazar sayısı: {coauthor_sayaci}")

                    for item in self.scene.items():
                        if isinstance(item, TiklanabilirElips) and item.author == yazar_a:
                            pen = QPen(QColor(255, 0, 0), 2)
                            item.setPen(pen)

                    for coauthor, _ in yazar_a.connections:
                        for item in self.scene.items():
                            if isinstance(item, TiklanabilirElips) and item.author == coauthor:
                                pen = QPen(QColor(255, 0, 0), 2)
                                item.setPen(pen)

                                start_x = item.rect().x() + item.rect().width() / 2
                                start_y = item.rect().y() + item.rect().height() / 2
                                author_x = next(i.rect().x() + i.rect().width() / 2 for i in self.scene.items() if isinstance(i, TiklanabilirElips) and i.author == yazar_a)
                                author_y = next(i.rect().y() + i.rect().height() / 2 for i in self.scene.items() if isinstance(i, TiklanabilirElips) and i.author == yazar_a)
                                line = self.scene.addLine(author_x, author_y, start_x, start_y, QColor(255, 0, 0, 150))
                                line.setPen(QPen(QColor(255, 0, 0, 150), 0.3, Qt.SolidLine))
                else:
                    self.output_area.append("Geçersiz yazar ID'si.")
        elif sender.text() == "6. İSTER":
            self.grafi_sifirla()
            en_cok_isbirligi_yapan_yazar, toplam_isbirligi = graf.en_cok_isbirligi_yapan_yazari_bul()
            self.output_area.clear()
            if en_cok_isbirligi_yapan_yazar:
                self.output_area.append(f"En cok işbirliği yapan yazar: {en_cok_isbirligi_yapan_yazar.name}, Toplam İşbirliği: {toplam_isbirligi}")
                for item in self.scene.items():
                    if isinstance(item, TiklanabilirElips) and item.author == en_cok_isbirligi_yapan_yazar:
                        pen = QPen(QColor(255, 0, 0), 2)
                        item.setPen(pen)
            else:
                self.output_area.append("Hiç yazar bulunamadı.")
        elif sender.text() == "7. İSTER":
            self.grafi_sifirla()
            orcid_a, ok_a = QInputDialog.getText(self, "Yazar ID'si", "Yazarın ORCID ID'sini girin:")
            if ok_a:
                yazar_a = next((yazar for yazar in graf.nodes if yazar.orcid == orcid_a), None)
                if yazar_a:
                    longest_path = graf.en_uzun_yol_bul(yazar_a.orcid)
                    self.output_area.clear()
                    if longest_path:
                        path_names = " -> ".join(author.name for author in longest_path)
                        self.output_area.append(f"En uzun yol: {path_names} (Düğüm Sayısı: {len(longest_path)})")
                        self.longest_path = longest_path
                        self.grafi_ciz()
                    else:
                        self.output_area.append("En uzun yol bulunamadı.")
                else:
                    self.output_area.append("Geçersiz yazar ID'si.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GrafArayuzu()
    window.show()
    sys.exit(app.exec_())