def warn(x):
    print(x)

def parse_cond(cond_list):
    if not cond_list:
        return None
    else:
        return Condition(cond_list)

def parse_tag_set(tagset_obj, tagset, filepath=True, splitted=False):
    if filepath:
        with open(tagset, 'r', encoding='utf-8') as ts:
            tagset = ts.read()
    
    if not splitted:
        tagset = tagset.splitlines()
    
    index = 0
    
    ## Retrieve languauge declaration:
    while index < len(tagset):
        line = tagset[index]
        
        if line.startswith('language'):
            lang, lang_code = line.split(' ')
            tagset_obj.lang = lang_code
        
        index += 1
    
    index = 0
    
    parts_of_speech = []
    
    while index < len(tagset):
        line = tagset[index]
        
        if not line or line.startswith('//'):
            pass
        else:
            if line.isupper():
                ## structure:
                ## for each Part-of-Speech:
                ## dictionary (attr_name) -> {attr_value1: condition1, attr_value2: condition2}
                ## Conditions - function that returns function that checks that condition is satisfied
                pos = line
                parts_of_speech.append(pos)
                attr_list = dict()
                index += 1
                line = tagset[index]
                while index < len(tagset) and not line.isupper():
                    if line:
                        attr, values = line.split('\t')
                        values = values.split(' ')
                        ## add condition expressions for possible values:
                        val_cond_dict = {value.split('#')[0]: [] for value in values if not value[0] in ('#','<')}
                        
                        ## handling value set inheritance
                        for value in values:
                            if value.startswith('<'):
                                minus_index = value.find('-')
                                parent_set, to_substr = value[:minus_index], value[minus_index:][1:]
                                to_substr = set(to_substr.split(','))
                                parent_set = parent_set.strip('<>')
                                parent_set = tagset_obj.__getattribute__(parent_set)[attr.split('#')[0]]
                                vals_to_set = set(i for i in parent_set)-to_substr
                                for key in vals_to_set:
                                    val_cond_dict[key] = [i for i in parent_set[key]]
                        
                        ## if attribute is available only under certain condition, retrieve this condition:
                        attr_cond_break = attr.find('#')
                        if attr_cond_break != -1:
                            attr, cond = attr.split('#')
                            for value in val_cond_dict:
                                val_cond_dict[value].append(cond)
                        
                        
                        ##if condition goes after space it is applicable to all
                        ## attribute values before it (after previous condition):
                        prev_index = 0
                        for ind, value in enumerate(values):
                            if value.startswith('#'):
                                for val in values[prev_index:ind]:
                                    if not val.startswith('#'):
                                        val_cond_dict[val.split('#')[0]].append(value[1:])
                                prev_index = ind+1
                        
                        ##if there is no space before confition then it is
                        ##applicable only to one attribute value before it:
                        for value in values:
                            if not value.startswith('#'):
                                if value.find('#') != -1:
                                    val_cond_dict[value.split('#')[0]].append(value.split('#')[1])
                        
                        ##convert lits of string conditions into Condition objects:
                        ##val_cond_dict = {i: parse_cond(val_cond_dict[i]) for i in val_cond_dict}
                        attr_list[attr] = val_cond_dict
                    index += 1
                    if index >= len(tagset):
                        break
                    line = tagset[index]
                tagset_obj.__setattr__(pos, attr_list)
                continue

        index += 1
    
    for pos in parts_of_speech:
        curr_pos = tagset_obj.__getattribute__(pos)
        for attr in curr_pos:
            curr_pos[attr] = {val:parse_cond(cond) for val, cond in curr_pos[attr].items()}
        tagset_obj.__setattr__(pos, curr_pos)

    return tagset_obj


class UDFeatsSet(object):
    def __init__(self, *args, **kwargs):
        parse_tag_set(self, *args, **kwargs)
    
    def check_tagset(self, pos_tag, tagset):
        ## first split tagset in key-value pairs;
        ## for each pair first check if it is allowed uncoditionally
        ## then check if it is allowed conditionally;
        ## if tis not allowed report an error
        if pos_tag in dir(self):
            tag_attr_dict = self.__getattribute__(pos_tag)
            for tag, value in tagset.items():
                if not tag in tag_attr_dict:
                    warn(f'feature "{tag}" not allowed for pos "{pos_tag}" for language "{self.lang}"')
                    continue
                if value in tag_attr_dict[tag]:
                    if not tag_attr_dict[tag][value]:
                        continue
                    elif tag_attr_dict[tag][value](tagset):
                        continue
                    warn(f'value "{value}" not allowed for feature "{tag}" for pos "{pos_tag}" for language "{self.lang}"')
                else:
                    warn(f'value "{value}" not allowed for feature "{tag}" for pos "{pos_tag}" for language "{self.lang}"')
        else:
            warn(f'POS {pos_tag} not allowed for language {self.lang}')

class Condition:
    def __init__(self, cond_list):
        self.allowed_values = dict()
        self.disallowed_values = dict()
        for condition in cond_list:
            condition = condition.strip('<>')
            neg = False
            if condition.startswith('!'):
                condition = condition[1:]
                neg = True
            ## here some code for parsing
            attr, values = condition.split('=')
            values = set(values.split(','))
            ## end of code for parsing
            if neg:
                if attr in self.disallowed_values:
                    self.disallowed_values[attr] |= values
                else:
                    self.disallowed_values[attr] = values
            else:
                if attr in self.allowed_values:
                    self.allowed_values[attr] &= values
                else:
                    self.allowed_values[attr] = values
    
    def __call__(self, tagset):
        if self.disallowed_values:
            for tag in tagset:
                if tag not in self.disallowed_values:
                    continue
                elif tagset[tag] in self.disallowed_values[tag]:
                    return False
        elif self.allowed_values:
            for tag in self.allowed_values:
                if tag not in tagset:
                    return False
                elif tagset[tag] not in self.allowed_values[tag]:
                    return False
        return True
    
    def __str__(self):
        return f'allowed values: {self.allowed_values}; disallowed_values: {self.disallowed_values}'
    
    __repr__ = __str__

