projects_list = [
    {
        'id' : 'prj1',
        'title' : 'RNA-seq study',
        'category' : 'Genomics',
        'order_date' : '25-05-2019',
        'delivery_date' : '17-07-2019',
        'status' : 'Delivered',
        'sensitive' : False,
        'description' : 'RNA-seq study on rats',
        'pi' : 'Illumina',
        'owner' : 'user1',
        'facility' : 'facility1',
        'size' : '40GB',
        'delivery_option' : 'DC_DDS',
        'public_key' : 'public_key',
        'private_key' : 'private_key',
        'salt' : 'salt',
        'nonce' : 'nonce'
    },
    {
        'id' : 'prj2',
        'title' : 'Whole genome reseq',
        'category' : 'Genomics',
        'order_date' : '09-09-2019',
        'delivery_date' : '30-11-2019',
        'status' : 'Delivered',
        'sensitive' : True,
        'description' : 'Human whole genome resequencing study',
        'pi' : 'Illumina',
        'owner' : 'user1',
        'facility' : 'facility1',
        'size' : '150GB',
        'delivery_option' : 'DC_DDS',
        'public_key' : 'public_key',
        'private_key' : 'private_key',
        'salt' : 'salt',
        'nonce' : 'nonce'
    },
    {
        'id' : 'prj3',
        'title' : 'Protein structure modelling',
        'category' : 'Proteomics',
        'order_date' : '15-09-2020',
        'delivery_date' : None,
        'status' : 'Ongoing',
        'sensitive' : False,
        'description' : 'Protein binding sites on bacteria',
        'pi' : 'Sanger',
        'owner' : 'user1',
        'facility' : 'facility2',
        'size' : None,
        'delivery_option' : 'DC_DDS',
        'public_key' : 'public_key',
        'private_key' : 'private_key',
        'salt' : 'salt',
        'nonce' : 'nonce'
    },
    {
        'id' : 'prj4',
        'title' : 'Corona expression study',
        'category' : 'Genomics',
        'order_date' : '03-09-2020',
        'delivery_date' : None,
        'status' : 'In facility',
        'sensitive' : True,
        'description' : 'Gene expressions of corona virus',
        'pi' : 'Illumina',
        'owner' : 'user1',
        'facility' : 'facility1',
        'size' : None,
        'delivery_option' : 'DC_DDS',
        'public_key' : 'public_key',
        'private_key' : 'private_key',
        'salt' : 'salt',
        'nonce' : 'nonce'
    }
]

files_list = [
    {
       'name': 'description.txt',
       'dpath': '',
       'size': '146 kb' 
    },
    {
        'name': 'Sample_1/data.txt',
        'dpath': 'Sample_1',
        'size': '10.3 mb'
    },
    {
        'name': 'Sample_1/source.txt',
        'dpath': 'Sample_1',
        'size': '257 kb'
    },
    {
        'name': 'Sample_1/meta/info.txt',
        'dpath': 'Sample_1/meta',
        'size': '96 kb'
    },
    {
        'name': 'Sample_2/data.txt',
        'dpath': 'Sample_2',
        'size': '8.7 mb'
    },
    {
        'name': 'Sample_2/source.txt',
        'dpath': 'Sample_2',
        'size': '350 kb'
    },
    {
        'name': 'Sample_2/meta/info.txt',
        'dpath': 'Sample_2/meta',
        'size': '67 kb'
    },
    {
        'name': 'sample_list.txt',
        'dpath': '',
        'size': '18 kb'
    },
    {
        'name': 'Plates/Sample_1/layout.txt',
        'dpath': 'Plates/Sample_1',
        'size': '79 kb'
    },
    {
        'name': 'Plates/Sample_2/layout.txt',
        'dpath': 'Plates/Sample_2',
        'size': '95 kb'
    }
]



