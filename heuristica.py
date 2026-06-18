"""
Furlan 1 – Solver Heurístico
Pipeline:
  1. Construção greedy multi-start aleatorizada
  2. Busca local completa (swap + or-opt) nas melhores soluções
  3. Simulated Annealing na melhor solução de busca local
  4. ILS: perturbação double-bridge + busca local rápida no tempo restante

Sem multi-thread. Sem dependências externas.
"""

import sys, math, random, time



def distancia(ax, ay, bx, by):
    return round(math.sqrt((bx - ax) ** 2 + (by - ay) ** 2))



def ler_arquivo(caminho):
    with open(caminho, encoding='utf-8') as arquivo:
        tokens = arquivo.read().split()
    pos = 0
    def proximo():
        nonlocal pos; valor = tokens[pos]; pos += 1; return valor

    alfa = float(proximo())
    beta = float(proximo())
    gama = float(proximo())
    phi  = float(proximo())

    num_semanas, num_cidades, num_equipes = int(proximo()), int(proximo()), int(proximo())

    cidades = []
    for _ in range(num_cidades):
        partes_nome = []
        while True:
            t = proximo()
            if t in ('True', 'False'):
                obrigatoria = (t == 'True')
                break
            partes_nome.append(t)
        nome = ' '.join(partes_nome)
        coord_x, coord_y, semanas_prep = int(proximo()), int(proximo()), int(proximo())
        disponivel    = [proximo() == 'True' for _ in range(num_semanas)]
        populacao_int = [int(proximo())      for _ in range(num_semanas)]
        cidades.append({
            'nome':          nome,
            'obrigatoria':   obrigatoria,
            'x':             coord_x,
            'y':             coord_y,
            'semanas_prep':  semanas_prep,
            'disponivel':    disponivel,
            'populacao_int': populacao_int,
        })

    equipes = []
    for _ in range(num_equipes):
        partes_nome = []
        while True:
            t = proximo()
            try: ex = int(t); break
            except ValueError: partes_nome.append(t)
        ey, dist_max = int(proximo()), int(proximo())
        equipes.append({
            'nome':     ' '.join(partes_nome),
            'x':        ex,
            'y':        ey,
            'dist_max': dist_max,
        })

    return alfa, beta, gama, phi, num_semanas, num_cidades, num_equipes, cidades, equipes



def cidade_pode_sediar(cidade, semana):
    #Verifica se a cidade pode sediar o evento na semana dada (índice 0).
    if not cidade['disponivel'][semana]:
        return False
    for k in range(1, cidade['semanas_prep'] + 1):
        semana_anterior = semana - k
        if semana_anterior >= 0 and not cidade['disponivel'][semana_anterior]:
            return False
    return True

def solucao_factivel(cidades, atribuicao, cidades_obrigatorias):
    #Verifica se a atribuição é factível: sem repetição, disponibilidade e obrigatórias.
    usadas = set()
    for semana, idx_cidade in enumerate(atribuicao):
        if idx_cidade in usadas or not cidade_pode_sediar(cidades[idx_cidade], semana):
            return False
        usadas.add(idx_cidade)
    return cidades_obrigatorias <= usadas

# função objetivo 

def criar_funcao_objetivo(alfa, beta, gama, phi, cidades, equipes):
    """
    Retorna (func_obj, matriz_dist, cache_reuniao).
    cache_reuniao[i] = (num_equipes_participantes, custo_reuniao) 
    quando a cidade i é a primeira do evento.
    """
    # cache de participação por cidade inicial
    cache_reuniao = {}
    for idx, cidade in enumerate(cidades):
        participantes = [e for e in equipes
                         if distancia(e['x'], e['y'], cidade['x'], cidade['y']) <= e['dist_max']]
        custo_reuniao = sum(distancia(e['x'], e['y'], cidade['x'], cidade['y'])
                            for e in participantes)
        cache_reuniao[idx] = (len(participantes), custo_reuniao)

    # matriz de distâncias entre cidades (calculada uma vez)
    M = len(cidades)
    matriz_dist = [[0] * M for _ in range(M)]
    for i in range(M):
        for j in range(i + 1, M):
            d = distancia(cidades[i]['x'], cidades[i]['y'],
                          cidades[j]['x'], cidades[j]['y'])
            matriz_dist[i][j] = d
            matriz_dist[j][i] = d

    def func_obj(atribuicao):
        num_semanas = len(atribuicao)
        primeira    = atribuicao[0]
        cidade_ini  = cidades[primeira]

        num_part, custo_reuniao = cache_reuniao[primeira]

        # distância do evento: percorre as cidades e volta para a primeira 
        custo_evento = sum(matriz_dist[atribuicao[k]][atribuicao[k + 1]]
                           for k in range(num_semanas - 1))
        custo_evento += matriz_dist[atribuicao[-1]][primeira]

        # total de pessoas que assistiram
        total_publico = sum(cidades[atribuicao[s]]['populacao_int'][s]
                            for s in range(num_semanas))

        return (alfa * custo_reuniao
                + beta * custo_evento
                - gama * total_publico
                - phi  * num_part)

    return func_obj, matriz_dist, cache_reuniao

# delta objetivo para swap

def delta_swap(pos_i, pos_j, atribuicao, alfa, beta, gama, phi,
               cidades, matriz_dist, cache_reuniao):
    """
    Calcula a variação no objetivo ao trocar as posições i e j,
    sem recalcular tudo do zero.
    """
    num_semanas = len(atribuicao)
    ci = atribuicao[pos_i]
    cj = atribuicao[pos_j]

    # variação de público
    delta_publico = (cidades[cj]['populacao_int'][pos_i]
                     + cidades[ci]['populacao_int'][pos_j]
                     - cidades[ci]['populacao_int'][pos_i]
                     - cidades[cj]['populacao_int'][pos_j])
    delta = -gama * delta_publico

    # variação nas arestas de distância do evento
    def aresta(a, b):
        if a < 0 or b < 0 or a >= num_semanas or b >= num_semanas:
            return 0
        return matriz_dist[atribuicao[a]][atribuicao[b]]

    dist_antes = (aresta(pos_i - 1, pos_i) + aresta(pos_i, pos_i + 1)
                + aresta(pos_j - 1, pos_j) + aresta(pos_j, pos_j + 1))
    # aresta de retorno à cidade inicial
    if pos_i == num_semanas - 1:
        dist_antes += matriz_dist[atribuicao[pos_i]][atribuicao[0]]
    if pos_j == num_semanas - 1:
        dist_antes += matriz_dist[atribuicao[pos_j]][atribuicao[0]]

    # simula o swap temporariamente
    atribuicao[pos_i], atribuicao[pos_j] = atribuicao[pos_j], atribuicao[pos_i]
    dist_depois = (aresta(pos_i - 1, pos_i) + aresta(pos_i, pos_i + 1)
                 + aresta(pos_j - 1, pos_j) + aresta(pos_j, pos_j + 1))
    if pos_i == num_semanas - 1:
        dist_depois += matriz_dist[atribuicao[pos_i]][atribuicao[0]]
    if pos_j == num_semanas - 1:
        dist_depois += matriz_dist[atribuicao[pos_j]][atribuicao[0]]
    atribuicao[pos_i], atribuicao[pos_j] = atribuicao[pos_j], atribuicao[pos_i]  # desfaz

    delta += beta * (dist_depois - dist_antes)

    # variação de reunião (só muda se a cidade inicial muda)
    if pos_i == 0 or pos_j == 0:
        nova_primeira = cj if pos_i == 0 else ci
        num_part_ant, custo_r_ant = cache_reuniao[atribuicao[0]]
        num_part_nov, custo_r_nov = cache_reuniao[nova_primeira]
        delta += alfa * (custo_r_nov - custo_r_ant) - phi * (num_part_nov - num_part_ant)

    return delta

# construção greedy 

def construir_greedy(num_semanas, cidades, matriz_dist, func_obj,
                     aleatorio, cidades_obrigatorias, top_k=4):
    """
    Constrói uma solução de forma greedy aleatorizada:
    - Obrigatórias primeiro (mais restrita primeiro)
    - Demais cidades escolhidas entre as top_k melhores (aleatoriedade controlada)
    """
    indices_opcionais    = [i for i, c in enumerate(cidades) if not c['obrigatoria']]
    indices_obrigatorios = [i for i, c in enumerate(cidades) if c['obrigatoria']]

    atribuicao = [None] * num_semanas
    usadas = set()

    # coloca obrigatórias: mais restrita (menos semanas disponíveis) primeiro
    obrig_ordenadas = sorted(
        indices_obrigatorios,
        key=lambda idx: sum(1 for s in range(num_semanas) if cidade_pode_sediar(cidades[idx], s))
    )
    for idx in obrig_ordenadas:
        semanas_possiveis = [s for s in range(num_semanas)
                             if atribuicao[s] is None and cidade_pode_sediar(cidades[idx], s)]
        if not semanas_possiveis:
            return None
        # escolhe a semana com maior público para essa cidade
        melhor_semana = max(semanas_possiveis, key=lambda s: cidades[idx]['populacao_int'][s])
        atribuicao[melhor_semana] = idx
        usadas.add(idx)

    # preenche semanas restantes
    for semana in range(num_semanas):
        if atribuicao[semana] is not None:
            continue
        candidatas = [idx for idx in indices_opcionais
                      if idx not in usadas and cidade_pode_sediar(cidades[idx], semana)]
        if not candidatas:
            return None

        # cidade anterior e próxima já alocadas (para estimar custo de distância)
        idx_anterior = next((atribuicao[s] for s in reversed(range(semana))
                             if atribuicao[s] is not None), None)
        idx_proxima  = next((atribuicao[s] for s in range(semana + 1, num_semanas)
                             if atribuicao[s] is not None), None)

        def pontuacao(idx):
            custo_dist = 0
            if idx_anterior is not None:
                custo_dist += matriz_dist[idx_anterior][idx]
            if idx_proxima is not None:
                custo_dist += matriz_dist[idx][idx_proxima]
            return custo_dist - cidades[idx]['populacao_int'][semana] * 50

        ranking = sorted(candidatas, key=pontuacao)
        k = max(1, min(top_k, len(ranking)))
        escolhida = aleatorio.choice(ranking[:k])
        atribuicao[semana] = escolhida
        usadas.add(escolhida)

    return atribuicao if None not in atribuicao else None

# busca local completa (swap + or-opt) 

def busca_local_completa(atribuicao, cidades, func_obj, cidades_obrigatorias,
                         matriz_dist, cache_reuniao, alfa, beta, gama, phi):
    melhor = list(atribuicao)
    melhor_obj = func_obj(melhor)
    n = len(melhor)

    # swap de posições
    melhorou = True
    while melhorou:
        melhorou = False
        for i in range(n):
            for j in range(i + 1, n):
                delta = delta_swap(i, j, melhor, alfa, beta, gama, phi,
                                   cidades, matriz_dist, cache_reuniao)
                if delta < -1e-9:
                    melhor[i], melhor[j] = melhor[j], melhor[i]
                    if solucao_factivel(cidades, melhor, cidades_obrigatorias):
                        melhor_obj += delta
                        melhorou = True
                    else:
                        melhor[i], melhor[j] = melhor[j], melhor[i]  # desfaz

    # or-opt (realocação de uma cidade)
    melhorou2 = True
    while melhorou2:
        melhorou2 = False
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                tentativa = melhor[:]
                cidade = tentativa.pop(i)
                tentativa.insert(j, cidade)
                if not solucao_factivel(cidades, tentativa, cidades_obrigatorias):
                    continue
                obj = func_obj(tentativa)
                if obj < melhor_obj - 1e-9:
                    melhor = tentativa
                    melhor_obj = obj
                    melhorou2 = True
                    break
            if melhorou2:
                break

    return melhor, melhor_obj

#  busca local rápida (swap, poucos passes) 

def busca_local_rapida(atribuicao, cidades, func_obj, cidades_obrigatorias,
                       matriz_dist, cache_reuniao, alfa, beta, gama, phi, passes=2):
    melhor = list(atribuicao)
    melhor_obj = func_obj(melhor)
    n = len(melhor)

    for _ in range(passes):
        melhorou = False
        for i in range(n):
            for j in range(i + 1, n):
                delta = delta_swap(i, j, melhor, alfa, beta, gama, phi,
                                   cidades, matriz_dist, cache_reuniao)
                if delta < -1e-9:
                    melhor[i], melhor[j] = melhor[j], melhor[i]
                    if solucao_factivel(cidades, melhor, cidades_obrigatorias):
                        melhor_obj += delta
                        melhorou = True
                    else:
                        melhor[i], melhor[j] = melhor[j], melhor[i]
        if not melhorou:
            break

    return melhor, melhor_obj

# simulated annealing 

def simulated_annealing(atribuicao, cidades, func_obj, cidades_obrigatorias,
                        matriz_dist, cache_reuniao, alfa, beta, gama, phi,
                        aleatorio, tempo_disponivel):
    n = len(atribuicao)
    atual = list(atribuicao)
    obj_atual = func_obj(atual)
    melhor = list(atual)
    melhor_obj = obj_atual

    # temperatura inicial proporcional ao valor do objetivo
    temperatura = max(abs(obj_atual) * 0.04, 0.5)
    resfriamento = 0.9997
    t0 = time.time()

    while time.time() - t0 < tempo_disponivel:
        temperatura *= resfriamento
        if temperatura < 1e-7:
            temperatura = max(abs(melhor_obj) * 0.01, 0.1)  # reaquece

        tipo_movimento = aleatorio.randint(0, 2)
        tentativa = atual[:]

        if tipo_movimento == 0:
            # swap de duas posições
            i, j = aleatorio.sample(range(n), 2)
            tentativa[i], tentativa[j] = tentativa[j], tentativa[i]
        elif tipo_movimento == 1:
            # or-opt: remove e reinsere em outro lugar
            i = aleatorio.randrange(n)
            j = aleatorio.randrange(n)
            cidade = tentativa.pop(i)
            tentativa.insert(j, cidade)
        else:
            # reversão de segmento
            if n >= 4:
                i, j = sorted(aleatorio.sample(range(n), 2))
                tentativa[i:j + 1] = tentativa[i:j + 1][::-1]
            else:
                i, j = aleatorio.sample(range(n), 2)
                tentativa[i], tentativa[j] = tentativa[j], tentativa[i]

        if not solucao_factivel(cidades, tentativa, cidades_obrigatorias):
            continue

        novo_obj = func_obj(tentativa)
        variacao = novo_obj - obj_atual
        if variacao < 0 or aleatorio.random() < math.exp(-variacao / temperatura):
            atual = tentativa
            obj_atual = novo_obj
            if obj_atual < melhor_obj - 1e-9:
                melhor = list(atual)
                melhor_obj = obj_atual

    return melhor, melhor_obj

# perturbação double-bridge 

def double_bridge(atribuicao, aleatorio):
    """
    Perturbação clássica para escapar de ótimos locais:
    divide a rota em 4 partes e as recombina de forma diferente.
    """
    n = len(atribuicao)
    if n < 4:
        copia = atribuicao[:]
        i, j = aleatorio.sample(range(n), 2)
        copia[i], copia[j] = copia[j], copia[i]
        return copia
    pontos_corte = sorted(aleatorio.sample(range(1, n), 3))
    a, b, c = pontos_corte
    return (atribuicao[:a] + atribuicao[b:c] +
            atribuicao[a:b] + atribuicao[c:])

#  solver principal 

def resolver(caminho_instancia, limite_tempo):
    alfa, beta, gama, phi, num_semanas, num_cidades, num_equipes, cidades, equipes = \
        ler_arquivo(caminho_instancia)

    func_obj, matriz_dist, cache_reuniao = criar_funcao_objetivo(
        alfa, beta, gama, phi, cidades, equipes)

    cidades_obrigatorias = {i for i, c in enumerate(cidades) if c['obrigatoria']}
    aleatorio = random.Random(42)
    t0 = time.time()
    tempo_decorrido = lambda: time.time() - t0

    #Fase 1: construção greedy multi-start (25% do tempo)
    pool_greedy = []
    for semente in range(5000):
        if tempo_decorrido() > limite_tempo * 0.25:
            break
        aleatorio.seed(semente)
        sol = construir_greedy(num_semanas, cidades, matriz_dist, func_obj,
                               aleatorio, cidades_obrigatorias, top_k=4)
        if sol and solucao_factivel(cidades, sol, cidades_obrigatorias):
            pool_greedy.append((func_obj(sol), sol))

    if not pool_greedy:
        for semente in range(10000):
            aleatorio.seed(semente + 99999)
            sol = construir_greedy(num_semanas, cidades, matriz_dist, func_obj,
                                   aleatorio, cidades_obrigatorias, top_k=1)
            if sol and solucao_factivel(cidades, sol, cidades_obrigatorias):
                pool_greedy.append((func_obj(sol), sol))
                break
    if not pool_greedy:
        return None, None

    pool_greedy.sort(key=lambda x: x[0])
    melhores_greedy = [sol for _, sol in pool_greedy[:20]]

    # Fase 2: busca local completa nas melhores greedy (25% do tempo)
    pool_bl = []
    for sol in melhores_greedy:
        if tempo_decorrido() > limite_tempo * 0.50:
            break
        sol_mel, obj_mel = busca_local_completa(
            sol, cidades, func_obj, cidades_obrigatorias,
            matriz_dist, cache_reuniao, alfa, beta, gama, phi)
        pool_bl.append((obj_mel, sol_mel))

    pool_bl.sort(key=lambda x: x[0])
    melhor_obj, melhor_sol = pool_bl[0]

    # Fase 3: simulated annealing (25% do tempo) 
    tempo_sa = limite_tempo * 0.25
    aleatorio.seed(7777)
    sol_sa, obj_sa = simulated_annealing(
        melhor_sol, cidades, func_obj, cidades_obrigatorias,
        matriz_dist, cache_reuniao, alfa, beta, gama, phi,
        aleatorio, tempo_sa)
    if obj_sa < melhor_obj - 1e-9:
        melhor_sol, melhor_obj = sol_sa, obj_sa

    # busca local completa depois do SA
    if tempo_decorrido() < limite_tempo * 0.82:
        melhor_sol, obj_pos_sa = busca_local_completa(
            melhor_sol, cidades, func_obj, cidades_obrigatorias,
            matriz_dist, cache_reuniao, alfa, beta, gama, phi)
        if obj_pos_sa < melhor_obj:
            melhor_obj = obj_pos_sa

    # Fase 4: ILS com busca local rápida (tempo restante)
    ils_melhor = list(melhor_sol)
    ils_melhor_obj = melhor_obj
    sem_melhora = 0
    aleatorio.seed(1234)

    while tempo_decorrido() < limite_tempo * 0.97:
        # perturbação double-bridge
        tentativa = double_bridge(ils_melhor, aleatorio)
        # se infactível, tenta corrigir com swaps aleatórios
        if not solucao_factivel(cidades, tentativa, cidades_obrigatorias):
            corrigido = False
            for _ in range(10):
                i, j = aleatorio.sample(range(num_semanas), 2)
                tentativa[i], tentativa[j] = tentativa[j], tentativa[i]
                if solucao_factivel(cidades, tentativa, cidades_obrigatorias):
                    corrigido = True; break
            if not corrigido:
                sem_melhora += 1; continue

        tentativa, obj_tent = busca_local_rapida(
            tentativa, cidades, func_obj, cidades_obrigatorias,
            matriz_dist, cache_reuniao, alfa, beta, gama, phi, passes=3)

        if obj_tent < ils_melhor_obj - 1e-9:
            ils_melhor = tentativa
            ils_melhor_obj = obj_tent
            sem_melhora = 0
        else:
            sem_melhora += 1
            # aceitação tipo SA 
            temp_ils = max(abs(ils_melhor_obj) * 0.003, 0.05)
            variacao = obj_tent - ils_melhor_obj
            if aleatorio.random() < math.exp(-max(variacao, 0) / temp_ils):
                ils_melhor = tentativa
                ils_melhor_obj = obj_tent

    if ils_melhor_obj < melhor_obj:
        melhor_sol = ils_melhor
        melhor_obj = ils_melhor_obj

    return melhor_sol, melhor_obj



if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Uso: python heuristica.py <instancia.txt> <saida.sol>")
        sys.exit(1)

    caminho_instancia = sys.argv[1]
    caminho_saida     = sys.argv[2]

    nome_arquivo = caminho_instancia.lower()
    limite_tempo = 4.5 if 'sprint' in nome_arquivo else 19.5

    atribuicao, valor_obj = resolver(caminho_instancia, limite_tempo)
    if atribuicao is None:
        sys.exit(1)

    _, _, _, _, _, _, _, cidades, _ = ler_arquivo(caminho_instancia)

    with open(caminho_saida, 'w', encoding='utf-8') as saida:
        for idx in atribuicao:
            saida.write(cidades[idx]['nome'].strip() + '\n')

    print(f"Objetivo: {valor_obj:.6f}")
    print("Rota:", " -> ".join(cidades[idx]['nome'].strip() for idx in atribuicao))