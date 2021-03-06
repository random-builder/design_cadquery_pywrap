from itertools import chain

from clang.cindex import CursorKind, TypeKind, AccessSpecifier
from path import Path

from .type_parser import parse_type
from .translation_unit import parse_tu
from .utils import current_platform

def paths_approximately_equal(p1,p2):
    '''Approximate path equality. This is due to
    '''
    return any([Path(p1).name.split('.')[0] == Path(p).name.split('.')[0] for p in p2])

def get_symbols(tu,kind,ignore_forwards=True):
    '''Symbols defined locally (i.e. without includes) and are not forward declarations
    '''
    tu_path = tu.path

    for child in tu.cursor.get_children():
        if paths_approximately_equal(Path(child.location.file.name),tu_path) \
        and child.kind == kind:
            if ignore_forwards:
                if child.get_definition() is None:
                    pass #forward declaration
                elif not paths_approximately_equal(Path(child.get_definition().location.file.name),tu_path):
                    pass #forward declaration but declared in an include
                else:
                    yield child #legitimate
            else:
                yield child

def get_forward_declarations(tu):
    '''Get all symbols that are forward declared'''
    tu_path = tu.path

    for child in tu.cursor.get_children():
        if paths_approximately_equal(Path(child.location.file.name),tu_path):
            if child.get_definition() is None:
                yield child

def get_all_symbols(tu,kind):
    '''All defined symbols of given kind
    '''
    tu_path = tu.path

    for child in tu.cursor.get_children():
        if paths_approximately_equal(Path(child.location.file.name),tu_path) \
        and child.kind is kind:
            yield child

def get_all_symbols_multi(tu,kinds):
    '''All defined symbols of given kinds
    '''
    tu_path = tu.path

    for child in tu.cursor.get_children():
        if paths_approximately_equal(Path(child.location.file.name),tu_path) \
        and any((child.kind is kind for kind in kinds)):
            yield child

def get_functions(tu):
    '''Functions defined locally (i.e. without includes)
    '''

    return (f for f in get_symbols(tu,CursorKind.FUNCTION_DECL,False) if 'operator' not in f.spelling)

def get_function_templates(tu):
    '''Function templates defined locally (i.e. without includes)
    '''

    return (f for f in get_symbols(tu,CursorKind.FUNCTION_TEMPLATE,False) if 'operator' not in f.spelling)

def get_operators(tu):
    '''Functions defined locally (i.e. without includes)
    '''

    return (f for f in get_symbols(tu,CursorKind.FUNCTION_DECL,False) if 'operator' in f.spelling)

def get_operator_templates(tu):
    '''Operator templates defined locally (i.e. without includes)
    '''

    return (f for f in get_symbols(tu,CursorKind.FUNCTION_TEMPLATE,False) if 'operator' in f.spelling)

def get_enums(tu):
    '''Enums defined locally (i.e. without includes)
    '''

    return get_symbols(tu,CursorKind.ENUM_DECL)

def get_enum_values(cur):
    '''Gets enum values
    '''

    for child in cur.get_children():
        if child.kind is CursorKind.ENUM_CONSTANT_DECL:
                yield child

def get_typedefs(tu):
    '''Typedefs defined locally (i.e. without includes)
    '''

    return get_symbols(tu,CursorKind.TYPEDEF_DECL)

def get_classes(tu):
    '''Classes defined locally (i.e. without includes)
    '''

    return  chain(get_symbols(tu,CursorKind.CLASS_DECL),
                  get_symbols(tu,CursorKind.STRUCT_DECL))

def get_class_templates(tu):
    '''Class templates defined locally (i.e. without includes)
    '''

    return  get_symbols(tu,CursorKind.CLASS_TEMPLATE)

def get_x(cls,kind):
    '''Get children entities of the specified type excluding forward declataions
    '''

    for child in cls.get_children():
        if child.kind is kind and child.get_definition():
                yield child

def get_x_multi(cls,kinds):
    '''Get children entities of the specified types excluding forward declataions
    '''

    for child in cls.get_children():
        if any((child.kind is kind for kind in kinds)) and child.get_definition():
            yield child

def get_xx(cls,kind,access):
    '''Get children entities of the specified type with given access specifier
    '''

    for child in cls.get_children():
        if child.kind is kind and child.access_specifier is access:
                yield child

def get_template_type_params(cls):
    '''Get all template type params
    '''

    for t in get_x_multi(cls,(CursorKind.TEMPLATE_TYPE_PARAMETER, CursorKind.TEMPLATE_NON_TYPE_PARAMETER)):
        if len(list(t.get_children())) == 0:
            yield t,None
        else:
            yield t,''.join([tok.spelling for tok in t.get_tokens()][3:])

def get_base_class(c):
    '''Get all class-baseclass pairs with public inheritance
    '''

    if c.get_definition():
        rv = [el for el in get_x(c.get_definition(),CursorKind.CXX_BASE_SPECIFIER) \
              if el.access_specifier is AccessSpecifier.PUBLIC]
    else:
        rv = [el for el in get_x(c,CursorKind.CXX_BASE_SPECIFIER) \
              if el.access_specifier is AccessSpecifier.PUBLIC]

    if len(rv) == 0:
        return []
    else:
        return [el.type.spelling for el in rv]

def get_inheritance_relations(tu):
    '''Inheritance relations pairs
    '''

    all_classes = get_x(tu.cursor,CursorKind.CLASS_DECL)

    for c in all_classes:
        yield c.spelling,get_base_class((c))

def get_public_methods(cls):
    '''Public methods of a given class
    '''

    for child in get_xx(cls,CursorKind.CXX_METHOD,AccessSpecifier.PUBLIC):
        if not child.is_static_method() and not child.spelling.startswith('operator'):
            yield child

def get_protected_pure_virtual_methods(cls):
    '''Protected pure virtual methods of a given class
    '''

    for child in get_xx(cls,CursorKind.CXX_METHOD,AccessSpecifier.PROTECTED):
        if not child.is_static_method() and not child.spelling.startswith('operator') and child.is_pure_virtual_method():
            yield child

def get_private_pure_virtual_methods(cls):
    '''Private pure virtual methods of a given class
    '''

    for child in get_xx(cls,CursorKind.CXX_METHOD,AccessSpecifier.PRIVATE):
        if not child.is_static_method() and not child.spelling.startswith('operator') and child.is_pure_virtual_method():
            yield child

def get_public_static_methods(cls):
    '''Public static methods of a given class
    '''

    for child in get_xx(cls,CursorKind.CXX_METHOD,AccessSpecifier.PUBLIC):
        if child.is_static_method() and not child.spelling.startswith('operator'):
            yield child

def get_public_operators(cls):
    '''Public operators of a given class
    '''

    for child in get_xx(cls,CursorKind.CXX_METHOD,AccessSpecifier.PUBLIC):
        if not child.is_static_method() and child.spelling.startswith('operator'):
            yield child

def get_public_static_operators(cls):
    '''Public static operators of a given class
    '''

    for child in get_xx(cls,CursorKind.CXX_METHOD,AccessSpecifier.PUBLIC):
        if child.is_static_method() and child.spelling.startswith('operator'):
            yield child

def get_public_constructors(cls):
    '''Public constructors of a given class
    '''

    for child in get_xx(cls,CursorKind.CONSTRUCTOR,AccessSpecifier.PUBLIC):
        yield child

def get_private_constructors(cls):
    '''Private constructors of a given class
    '''

    for child in get_xx(cls,CursorKind.CONSTRUCTOR,AccessSpecifier.PRIVATE):
        yield child

def get_protected_constructors(cls):
    '''Protected constructors of a given class
    '''

    for child in get_xx(cls,CursorKind.CONSTRUCTOR,AccessSpecifier.PROTECTED):
        yield child


def get_public_destructors(cls):
    '''Public destructors of a given class
    '''

    for child in get_xx(cls,CursorKind.DESTRUCTOR,AccessSpecifier.PUBLIC):
        yield child

def get_private_destructors(cls):
    '''Private destructors of a given class
    '''

    for child in get_xx(cls,CursorKind.DESTRUCTOR,AccessSpecifier.PRIVATE):
        yield child

def get_protected_destructors(cls):
    '''Private destructors of a given class
    '''

    for child in get_xx(cls,CursorKind.DESTRUCTOR,AccessSpecifier.PROTECTED):
        yield child

def get_free_method_definitions(tu):
    '''Free method definitions
    '''

    return (el for el in get_symbols(tu,CursorKind.CXX_METHOD) \
            if not el.is_static_method() \
            and el.access_specifier==AccessSpecifier.PUBLIC)

class BaseInfo(object):
    '''Base class for the info objects
    '''

    def __init__(self,cur):

        self.name = cur.spelling
        self.comment = cur.brief_comment


class EnumInfo(BaseInfo):
    '''Container for enum parsing results
    '''

    def __init__(self,cur):

        super(EnumInfo,self).__init__(cur)

        self.comment = cur.brief_comment
        self.values = [el.spelling for el in get_enum_values(cur)]
        self.anonymous = False

        if self.name == '':
            name = cur.type.spelling
            if 'anonymous' in name:
                self.anonymous = True
            else:
                self.name = name

class FunctionInfo(BaseInfo):
    '''Container for function parsing results
    '''

    KIND_DICT = {TypeKind.LVALUEREFERENCE : ' &',
                 TypeKind.RVALUEREFERENCE : ' &&',
                 TypeKind.POINTER : ' *'}

    def __init__(self,cur):

        super(FunctionInfo,self).__init__(cur)

        self.comment = cur.brief_comment
        self.full_name = cur.displayname
        self.mangled_name = cur.mangled_name
        self.return_type = cur.result_type.spelling
        self.inline = cur.get_definition().is_inline() if cur.get_definition() else False
        self.pointer_by_ref = any(self._pointer_by_ref(el) for el in cur.get_arguments())
        self.args = [(el.spelling,self._underlying_type(el),self._default_value(el)) for el in cur.get_arguments()]
        self.default_value_types = [self._underlying_type(el,False) for el in cur.get_arguments() if self._default_value(el)]


    def _pointer_by_ref(self,cur):
        '''Check is type is a Pointer passed by reference
        '''

        rv = False
        t = cur.type

        # if passed by ref
        if t.kind == TypeKind.LVALUEREFERENCE:
            tp = t.get_pointee().get_canonical()
            # if underlying type is a pointer
            if tp.kind in (TypeKind.POINTER,):
                rv = True

        return rv

    def _underlying_type(self,cur,add_qualifiers=True):
        '''Tries to resolve the underlying type. Needed for typedefed templates.
        '''

        ptr = self.KIND_DICT.get(cur.type.kind,'')

        # if lvaule,rvalue or pointer type
        if ptr:
            const_ptr = ' const ' if cur.type.is_const_qualified() else ''
            pointee = cur.type.get_pointee()
            const = ' const ' if pointee.is_const_qualified() else ''
            decl = pointee.get_declaration()
        else:
            const_ptr = ''
            const = ' const ' if cur.type.is_const_qualified() else ''
            decl = cur.type.get_declaration()

        # if typedef that is not POD
        if decl.kind == CursorKind.TYPEDEF_DECL and not decl.underlying_typedef_type.is_pod():
            spelling = decl.underlying_typedef_type.spelling
            if add_qualifiers:
                rv=const+spelling+ptr+const_ptr
            else:
                rv=spelling
        else:
            rv = cur.type.spelling

        # strip possible opencascade::handle<T> when
        if not add_qualifiers:
            rv = parse_type(rv)

        return rv

    def _default_value(self,cur):
        '''Tries to extract default value
        '''

        rv = None
        tokens = [t.spelling for t in cur.get_tokens()]
        if '=' in tokens:
            rv = ' '.join(tokens[tokens.index('=')+1:])

        return rv




class MethodInfo(FunctionInfo):
    '''Container for method parsing results
    '''

    def __init__(self,cur):

        super(MethodInfo,self).__init__(cur)

        self.const = cur.is_const_method()
        self.virtual = cur.is_virtual_method()
        self.pure_virtual = cur.is_pure_virtual_method()

class ConstructorInfo(MethodInfo):
    '''Container for constructor parsing results
    '''

    pass

class DestructorInfo(FunctionInfo):
    '''Container for destructor parsing results
    '''

    pass

class ClassInfo(object):
    '''Container for class parsing results
    '''

    def __init__(self,cur):

        self.name = cur.type.spelling
        self.comment = cur.brief_comment
        self.abstract = cur.is_abstract_record()

        self.constructors = self.filter_rvalues((ConstructorInfo(el) for el in get_public_constructors(cur)))
        self.nonpublic_constructors = [ConstructorInfo(el) for el in get_private_constructors(cur)]\
            + [ConstructorInfo(el) for el in get_protected_constructors(cur)]

        self.methods = self.filter_rvalues((MethodInfo(el) for el in get_public_methods(cur)))
        self.protected_virtual_methods = self.filter_rvalues((MethodInfo(el) for el in get_protected_pure_virtual_methods(cur)))
        self.private_virtual_methods = self.filter_rvalues((MethodInfo(el) for el in get_private_pure_virtual_methods(cur)))

        self.static_methods = self.filter_rvalues((MethodInfo(el) for el in get_public_static_methods(cur)))
        
        self.static_methods_byref = []
        self.methods_byref = []

        self.operators = [MethodInfo(el) for el in get_public_operators(cur)]
        self.static_operators = [MethodInfo(el) for el in get_public_static_operators(cur)]

        self.destructors = [DestructorInfo(el) for el in get_public_destructors(cur)]
        self.nonpublic_destructors = [DestructorInfo(el) for el in get_private_destructors(cur)]\
            + [DestructorInfo(el) for el in get_protected_destructors(cur)]

        self.ptr = None
        self.superclass = []
        self.rootclass = []
        self.superclasses = []

        self.methods_dict = {m.name:m for m in self.methods}
        self.protected_virtual_methods_dict = {m.name:m for m in self.protected_virtual_methods}
        self.private_virtual_methods_dict = {m.name:m for m in self.private_virtual_methods}

    def filter_rvalues(self,funcs):

        return [f for f in funcs if not any(('&&' in arg for _,arg,_ in f.args))]

    def extend_defintion(self,other):

        new_comment = ''
        if self.comment:
            new_comment += self.comment
        if other.comment:
            new_comment += other.comment
        self.comment = new_comment

        self.constructors += other.constructors
        self.nonpublic_constructors +=  other.nonpublic_constructors
        self.methods += other.methods
        self.protected_virtual_methods += other.protected_virtual_methods
        self.private_virtual_methods += other.private_virtual_methods
        self.static_methods += other.static_methods
        self.operators += other.operators
        self.static_operators += other.static_operators
        self.destructors += other.destructors
        self.nonpublic_destructors +=  other.nonpublic_destructors

        self.methods_dict = {**self.methods_dict,**other.methods_dict}
        self.protected_virtual_methods_dict = {**self.protected_virtual_methods_dict,**other.protected_virtual_methods_dict}
        self.private_virtual_methods_dict = {**self.protected_virtual_methods_dict,**other.protected_virtual_methods_dict}

class ClassTemplateInfo(ClassInfo):

    def __init__(self,cur):

         super(ClassTemplateInfo,self).__init__(cur)
         self.name = cur.spelling
         self.type_params = [(None if el.spelling == el.type.spelling else el.type.spelling,
                              el.spelling,
                              default) for el,default in get_template_type_params(cur)]

class TypedefInfo(BaseInfo):

    def __init__(self,cur):

        super(TypedefInfo,self).__init__(cur)

        t = cur.underlying_typedef_type

        self.type = t.spelling
        self.pod = t.is_pod()

        if not self.pod:
            self.template_base = [ch.spelling for ch in cur.get_children() if ch.kind == CursorKind.TEMPLATE_REF]
            self.template_args = [ch.spelling for ch in cur.get_children() if ch.kind == CursorKind.TYPE_REF]

class ForwardInfo(BaseInfo):

    pass

class HeaderInfo(object):
    '''Container for header parsing results
    '''

    def __init__(self):

        self.dependencies = []
        self.classes = {}
        self.functions = []
        self.enums = []
        self.methods = []
        self.inheritance = {}
        self.typedefs = {}
        self.forwards = []

    def resolve_inheritance(self,cls):

        inheritance = self.inheritance
        superclasses = cls.superclasses
        rootclass = cls.rootclass
        
        cls.superclass = inheritance.get(cls.name,[])
        
        def _resolve_inheritance(node):
            '''Recurisvely traverse the inheritance tree'''
            
            for el in node:
                superclasses.append(el)
                
                if el in inheritance:
                    _resolve_inheritance(inheritance[el])
                else:
                    rootclass.append(el)
        
        _resolve_inheritance(cls.superclass)


    def parse(self, path,input_folder,settings):

        tr_unit = parse_tu(path,
                           input_folder,
                           prefix=settings[current_platform()]['prefix'],
                           platform_includes=settings[current_platform()]['includes'],
                           parsing_header=settings['parsing_header'],
                           platform_parsing_header=settings[current_platform()]['parsing_header'])

        self.name = path
        self.short_name = path.splitpath()[-1]
        self.dependencies = [el.location.file.name for el in tr_unit.get_includes()]
        self.enums = [EnumInfo(el) for el in get_enums(tr_unit)]
        self.functions = [FunctionInfo(el) for el in get_functions(tr_unit)]
        self.operators = [FunctionInfo(el) for el in get_operators(tr_unit)]

        self.classes = {}
        for el in get_classes(tr_unit):
            if el.displayname in self.classes:
                self.classes[el.displayname].extend_defintion(ClassInfo(el))
            else:
                self.classes[el.displayname] = ClassInfo(el)

        self.class_dict = {k : self.name for k in self.classes}
        self.class_templates = {el.displayname:ClassTemplateInfo(el) for el in get_class_templates(tr_unit)}
        self.inheritance = {k:v for k,v in get_inheritance_relations(tr_unit) if v}
        self.typedefs = [TypedefInfo(el) for el in get_typedefs(tr_unit)]
        self.typedef_dict = {t.name : self.name for t in self.typedefs}
        self.forwards = [ForwardInfo(el) for el in get_forward_declarations(tr_unit)]

        #handle freely defined methods
        methods = [el for el in get_free_method_definitions(tr_unit)]

        #match methods to classes
        for m in methods:
            cls = self.classes.get(m.semantic_parent.displayname,None)
            if cls:
                cls.methods.append(MethodInfo(m))

        #resolve inheritance relations
        for c in self.classes.values():
            self.resolve_inheritance(c)

        return tr_unit

def process_header(path,input_folder,settings):
    '''Main function from this module
    '''

    hi = HeaderInfo()
    hi.parse(path,input_folder,settings)

    return hi

__all__ = [process_header,]

if __name__ == '__main__':

    from os import getenv
    from .utils import init_clang
    init_clang()

    conda_prefix = Path(getenv('CONDA_PREFIX'))

    gp_Ax1 = process_header(conda_prefix /  'include' / 'opencascade' / 'gp_Ax1.hxx')

    for el in gp_Ax1.classes.values():
        print(el.name)

    #try public methods
    for el in el.methods:
        print(el.name,el.args,el.return_type)

    #try enums
    gp_TrsfForm = \
    process_header(conda_prefix /  'include' / 'opencascade' / 'gp_TrsfForm.hxx')

    for el in gp_TrsfForm.enums:
        print(el.name)
        print(el.values)

    #try functions
    gp_Vec2d = process_header(conda_prefix /  'include' / 'opencascade' / 'gp_Vec2d.hxx')

    for el in gp_Vec2d.functions:
        print(el.name)

    for el in gp_Vec2d.operators:
        print(el.name)

    #try inheritance
    TopoDS = process_header(conda_prefix /  'include' / 'opencascade' / 'TopoDS_Solid.hxx')

    for k in TopoDS.inheritance:
        print(k,TopoDS.inheritance[k])
